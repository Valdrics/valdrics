from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional
from uuid import UUID

import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.models.llm import LLMBudget
from app.shared.core.constants import LLMProvider
from app.shared.core.exceptions import AIAnalysisError, BudgetExceededError
from app.shared.core.pricing import PricingTier
from app.shared.core.config import get_settings
from app.shared.llm.budget_manager import BudgetStatus, LLMBudgetManager
from app.shared.llm.factory import LLMFactory

tracer = trace.get_tracer(__name__)
logger = structlog.get_logger()


def _normalize_provider(value: Any) -> str:
    if isinstance(value, LLMProvider):
        return value.value
    if isinstance(value, str):
        return value.lower()
    return ""


async def setup_client_and_usage(
    *,
    tenant_id: Optional[UUID],
    db: Optional[AsyncSession],
    provider: Optional[str],
    model: Optional[str],
    budget_manager: Any = LLMBudgetManager,
    llm_budget_model: Any = LLMBudget,
    settings_provider: Callable[[], Any] = get_settings,
    logger_obj: Any = logger,
) -> tuple[str, str, Optional[str]]:
    """Resolve effective provider/model and optional BYOK credentials."""
    byok_key = None
    budget = None
    budget_status = None

    if tenant_id and db:
        budget_status = await budget_manager.check_budget(tenant_id, db)
        if budget_status == BudgetStatus.HARD_LIMIT:
            raise BudgetExceededError("Monthly LLM budget exceeded (Hard Limit).")

        result = await db.execute(
            select(llm_budget_model).where(llm_budget_model.tenant_id == tenant_id)
        )
        budget = result.scalar_one_or_none()
        if budget:
            keys: dict[str, str | None] = {
                LLMProvider.OPENAI: budget.openai_api_key,
                LLMProvider.ANTHROPIC: budget.claude_api_key,
                LLMProvider.GOOGLE: budget.google_api_key,
                LLMProvider.GROQ: budget.groq_api_key,
                LLMProvider.AZURE: getattr(budget, "azure_api_key", None),
            }
            requested_provider = _normalize_provider(provider) or _normalize_provider(
                budget.preferred_provider
            )
            byok_key = keys.get(requested_provider)

    valid_models: dict[str, list[str]] = {
        LLMProvider.OPENAI.value: [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
        ],
        LLMProvider.ANTHROPIC.value: [
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-5-sonnet",
            "claude-3-5-haiku",
        ],
        LLMProvider.GOOGLE.value: [
            "gemini-pro",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        LLMProvider.GROQ.value: [
            "llama-3.3-70b-versatile",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant",
        ],
        LLMProvider.AZURE.value: ["gpt-4", "gpt-35-turbo"],
    }

    preferred_provider = provider or (
        budget.preferred_provider if budget else settings_provider().LLM_PROVIDER
    )
    effective_provider = _normalize_provider(preferred_provider) or LLMProvider.GROQ.value
    effective_model = str(
        model or (budget.preferred_model if budget else "llama-3.3-70b-versatile")
    )

    if tenant_id and db and budget_status == BudgetStatus.SOFT_LIMIT:
        logger_obj.warning("llm_budget_soft_limit_degradation", tenant_id=str(tenant_id))
        if effective_provider == LLMProvider.GROQ.value:
            effective_model = "llama-3.1-8b-instant"
        elif effective_provider == LLMProvider.OPENAI.value:
            effective_model = "gpt-4o-mini"
        elif effective_provider == LLMProvider.GOOGLE.value:
            effective_model = "gemini-1.5-flash"
        elif effective_provider == LLMProvider.ANTHROPIC.value:
            effective_model = "claude-3-5-haiku"

    if effective_provider not in valid_models:
        logger_obj.warning("invalid_llm_provider_rejected", provider=effective_provider)
        effective_provider = settings_provider().LLM_PROVIDER
        effective_model = "llama-3.3-70b-versatile"

    allowed_models = valid_models.get(effective_provider, [])
    if effective_model not in allowed_models:
        if not (byok_key and re.match(r"^[a-zA-Z0-9\.\-\:\/]+$", str(effective_model))):
            logger_obj.warning(
                "unsupported_model_fallback",
                provider=effective_provider,
                model=effective_model,
            )
            effective_model = (
                allowed_models[0] if allowed_models else "llama-3.3-70b-versatile"
            )

    return effective_provider, effective_model, byok_key


async def invoke_llm(
    *,
    llm: BaseChatModel,
    prompt_template: ChatPromptTemplate,
    formatted_data: str,
    provider: str,
    model: str,
    byok_key: Optional[str],
    max_output_tokens: Optional[int],
    tenant_tier: PricingTier | None,
    bind_output_token_ceiling: Callable[[BaseChatModel, int], Any],
    llm_factory: Any = LLMFactory,
    settings_provider: Callable[[], Any] = get_settings,
    tracer_obj: Any = tracer,
    logger_obj: Any = logger,
) -> tuple[str, dict[str, Any]]:
    """Run LLM invocation with retries and tenant-tier-aware fallback chain."""
    current_llm: Any = llm
    if max_output_tokens is not None and max_output_tokens > 0:
        if provider == settings_provider().LLM_PROVIDER and not byok_key:
            bound = bind_output_token_ceiling(current_llm, max_output_tokens)
            if bound is not None:
                current_llm = bound
            else:
                current_llm = llm_factory.create(
                    provider,
                    model=model,
                    api_key=byok_key,
                    max_output_tokens=max_output_tokens,
                )
        else:
            current_llm = llm_factory.create(
                provider,
                model=model,
                api_key=byok_key,
                max_output_tokens=max_output_tokens,
            )
    elif provider != settings_provider().LLM_PROVIDER or byok_key:
        current_llm = llm_factory.create(provider, model=model, api_key=byok_key)

    chain = prompt_template | current_llm

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _invoke_with_retry() -> tuple[str, dict[str, Any]]:
        logger_obj.info("invoking_llm", provider=provider, model=model)
        response = await chain.ainvoke({"cost_data": formatted_data})
        content = response.content
        safe_content = content if isinstance(content, str) else json.dumps(content, default=str)
        metadata = getattr(response, "response_metadata", {})
        return safe_content, metadata if isinstance(metadata, dict) else {}

    low_cost_chain: list[tuple[str, str]] = [
        (LLMProvider.GROQ.value, "llama-3.1-8b-instant"),
        (LLMProvider.GOOGLE.value, "gemini-1.5-flash"),
    ]
    extended_chain: list[tuple[str, str]] = low_cost_chain + [
        (LLMProvider.OPENAI.value, "gpt-4o-mini"),
    ]
    enterprise_chain: list[tuple[str, str]] = extended_chain + [
        (LLMProvider.ANTHROPIC.value, "claude-3-5-haiku"),
    ]
    if byok_key:
        fallback_candidates: list[tuple[str, str]] = []
    elif tenant_tier in {PricingTier.PRO}:
        fallback_candidates = extended_chain
    elif tenant_tier == PricingTier.ENTERPRISE:
        fallback_candidates = enterprise_chain
    else:
        fallback_candidates = low_cost_chain

    with tracer_obj.start_as_current_span("llm_invocation") as span:
        span.set_attribute("llm.provider", provider)
        span.set_attribute("llm.model", model)
        try:
            return await _invoke_with_retry()
        except (
            AIAnalysisError,
            RuntimeError,
            ValueError,
            TypeError,
            OSError,
        ) as primary_error:  # noqa: BLE001
            logger_obj.warning(
                "llm_primary_failed_trying_fallbacks",
                provider=provider,
                error=str(primary_error),
            )
            for fallback_provider, fallback_model in fallback_candidates:
                if fallback_provider == provider:
                    continue
                try:
                    fallback_llm = llm_factory.create(
                        fallback_provider,
                        model=fallback_model,
                        max_output_tokens=max_output_tokens,
                    )
                    fallback_chain = prompt_template | fallback_llm
                    logger_obj.info(
                        "trying_fallback_llm",
                        provider=fallback_provider,
                        model=fallback_model,
                    )
                    response = await fallback_chain.ainvoke({"cost_data": formatted_data})
                    content = response.content
                    safe_content = (
                        content if isinstance(content, str) else json.dumps(content, default=str)
                    )
                    metadata = getattr(response, "response_metadata", {})
                    span.set_attribute("llm.fallback_used", True)
                    span.set_attribute("llm.fallback_provider", fallback_provider)
                    return safe_content, metadata if isinstance(metadata, dict) else {}
                except (
                    AIAnalysisError,
                    RuntimeError,
                    ValueError,
                    TypeError,
                    OSError,
                ) as fallback_error:  # noqa: BLE001
                    logger_obj.warning(
                        "llm_fallback_failed",
                        provider=fallback_provider,
                        error=str(fallback_error),
                    )
                    continue

            logger_obj.error("llm_all_providers_failed", primary_provider=provider)
            raise AIAnalysisError(
                f"All LLM providers failed. Primary: {provider}, Error: {str(primary_error)}"
            )
