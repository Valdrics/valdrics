# mypy: disable-error-code=import-untyped
from __future__ import annotations

import asyncio
import copy
import json
import os
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional, cast
from uuid import UUID

import structlog
import yaml
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from opentelemetry import trace
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import stop_after_attempt, wait_exponential  # noqa: F401

from app.models.llm import LLMBudget
from app.modules.notifications.domain import get_slack_service, get_tenant_slack_service
from app.shared.analysis.forecaster import SymbolicForecaster
from app.shared.core.cache import get_cache_service
from app.shared.core.config import get_settings
from app.shared.core.exceptions import AIAnalysisError, BudgetExceededError
from app.shared.core.pricing import PricingTier, get_tenant_tier, get_tier_limit
from app.shared.llm.analyzer_cache import check_cache_and_delta
from app.shared.llm.analyzer_limits import (
    apply_tier_analysis_shape_limits,
    bind_output_token_ceiling,
    normalize_analysis_payload,
    record_to_date,
    resolve_output_token_ceiling,
    resolve_positive_limit,
    strip_markdown,
)
from app.shared.llm.analyzer_results import (
    check_and_alert_anomalies,
    process_analysis_results,
)
from app.shared.llm.budget_manager import LLMBudgetManager
from app.shared.llm.factory import LLMFactory
from app.shared.llm.guardrails import FinOpsAnalysisResult, LLMGuardrails
from app.shared.llm.llm_client import invoke_llm, setup_client_and_usage

if TYPE_CHECKING:
    from app.schemas.costs import CloudUsageSummary

tracer = trace.get_tracer(__name__)
logger = structlog.get_logger()

# System prompts are now managed in prompts.yaml
FINOPS_ANALYSIS_SCHEMA_VERSION = "valdrics.finops.analysis.v1"
FINOPS_PROMPT_FALLBACK_VERSION = "valdrics.finops.prompt.fallback.v1"
FINOPS_RESPONSE_NORMALIZER_VERSION = "valdrics.finops.response-normalizer.v1"


class FinOpsAnalyzer:
    """
    The 'Brain' of Valdrics.

    This class wraps a LangChain ChatModel and orchestrates cloud cost analysis.
    """

    def __init__(self, llm: BaseChatModel, db: Optional[AsyncSession] = None):
        self.llm = llm
        self.db = db
        self.prompt: Optional[ChatPromptTemplate] = None
        self.prompt_version: str = FINOPS_PROMPT_FALLBACK_VERSION

    async def _get_prompt(self) -> ChatPromptTemplate:
        """Load and cache the prompt template asynchronously."""
        if self.prompt is not None:
            return self.prompt

        system_prompt = await self._load_system_prompt_async()
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("user", "Analyze this cloud cost data:\n{cost_data}"),
            ]
        )
        return self.prompt

    async def _load_system_prompt_async(self) -> str:
        """Load system prompt from YAML in a thread pool or use fallback."""
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts.yaml")

        try:
            if os.path.exists(prompt_path):
                loop = asyncio.get_running_loop()

                def _read_file() -> Any:
                    with open(prompt_path, "r") as f:
                        return yaml.safe_load(f)

                registry = await loop.run_in_executor(None, _read_file)
                if isinstance(registry, dict) and "finops_analysis" in registry:
                    prompt_entry = registry["finops_analysis"]
                    if isinstance(prompt_entry, dict):
                        prompt_version = prompt_entry.get("version")
                        if isinstance(prompt_version, str) and prompt_version.strip():
                            self.prompt_version = prompt_version.strip()
                        prompt = prompt_entry.get("system")
                    else:
                        prompt = None
                    if isinstance(prompt, str) and prompt.strip():
                        return prompt
        except (
            OSError,
            yaml.YAMLError,
            ValueError,
            TypeError,
            RuntimeError,
        ) as exc:  # noqa: BLE001
            logger.error("failed_to_load_prompts_yaml", error=str(exc), path=prompt_path)

        self.prompt_version = FINOPS_PROMPT_FALLBACK_VERSION
        logger.warning("using_fallback_system_prompt")
        return (
            "You are a FinOps expert. Analyze the provided cloud cost data. "
            "Identify anomalies, waste, and optimization opportunities. "
            "You MUST return the analysis in valid JSON format only, "
            "with the keys: 'summary', 'anomalies' (list), 'recommendations' (list), "
            "and 'estimated_total_savings'."
        )

    def _strip_markdown(self, text: str) -> str:
        return strip_markdown(text)

    @staticmethod
    def _resolve_output_token_ceiling(raw_limit: Any) -> int | None:
        return resolve_output_token_ceiling(raw_limit)

    @staticmethod
    def _resolve_positive_limit(
        raw_limit: Any,
        *,
        minimum: int = 1,
        maximum: int = 1_000_000,
    ) -> int | None:
        return resolve_positive_limit(raw_limit, minimum=minimum, maximum=maximum)

    @staticmethod
    def _record_to_date(value: Any) -> Any:
        return record_to_date(value)

    @classmethod
    def _apply_tier_analysis_shape_limits(
        cls,
        usage_summary: "CloudUsageSummary",
        *,
        tenant_tier: PricingTier,
    ) -> tuple["CloudUsageSummary", dict[str, int]]:
        return apply_tier_analysis_shape_limits(
            usage_summary,
            tenant_tier=tenant_tier,
            get_tier_limit_fn=get_tier_limit,
        )

    @staticmethod
    def _bind_output_token_ceiling(llm: BaseChatModel, max_output_tokens: int) -> Any:
        return bind_output_token_ceiling(llm, max_output_tokens)

    @staticmethod
    def _normalize_analysis_payload(llm_result: dict[str, Any]) -> dict[str, Any]:
        return normalize_analysis_payload(llm_result)

    async def analyze(
        self,
        usage_summary: "CloudUsageSummary",
        tenant_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        force_refresh: bool = False,
        user_id: Optional[UUID] = None,
        client_ip: Optional[str] = None,
    ) -> dict[str, Any]:
        """Analyze cloud costs with budget pre-authorization and deterministic guardrails."""
        operation_id = str(uuid.uuid4())
        effective_db = db or self.db

        with tracer.start_as_current_span("analyze_costs") as span:
            span.set_attribute("tenant_id", str(tenant_id) if tenant_id else "anonymous")
            span.set_attribute("operation_id", operation_id)

            cached_analysis, is_delta = await self._check_cache_and_delta(
                tenant_id, force_refresh, usage_summary
            )
            if cached_analysis and not is_delta:
                logger.info(
                    "analysis_cache_hit",
                    tenant_id=str(tenant_id),
                    operation_id=operation_id,
                )
                return cached_analysis

            records_for_analysis = getattr(
                usage_summary,
                "_analysis_records_override",
                usage_summary.records,
            )
            if records_for_analysis is usage_summary.records:
                usage_summary_to_analyze = usage_summary
            else:
                usage_summary_to_analyze = copy.copy(usage_summary)
                usage_summary_to_analyze.records = records_for_analysis
                if hasattr(usage_summary, "_analysis_records_override"):
                    delattr(usage_summary, "_analysis_records_override")

            logger.info(
                "starting_analysis",
                tenant_id=str(tenant_id),
                data_points=len(usage_summary_to_analyze.records),
                mode="delta" if is_delta else "full",
                operation_id=operation_id,
            )

            tenant_tier: PricingTier | None = None
            shape_limits: dict[str, int] = {}
            if tenant_id and effective_db:
                tenant_tier = await get_tenant_tier(tenant_id, effective_db)
                usage_summary_to_analyze, shape_limits = self._apply_tier_analysis_shape_limits(
                    usage_summary_to_analyze,
                    tenant_tier=tenant_tier,
                )
                if shape_limits.get("records_after", 0) < shape_limits.get(
                    "records_before", 0
                ):
                    logger.info(
                        "llm_analysis_shape_limited",
                        tenant_id=str(tenant_id),
                        tier=tenant_tier.value,
                        limits=shape_limits,
                    )

            reserved_amount: Decimal | None = None
            max_output_tokens: int | None = None
            max_prompt_tokens: int | None = None
            actor_type = "user" if user_id else "system"

            llm_model = getattr(
                self.llm,
                "model_name",
                getattr(self.llm, "model", "llama-3.3-70b-versatile"),
            )
            effective_model = model or llm_model

            try:
                if tenant_id and effective_db:
                    if tenant_tier is None:
                        tenant_tier = await get_tenant_tier(tenant_id, effective_db)
                    max_output_tokens = self._resolve_output_token_ceiling(
                        get_tier_limit(tenant_tier, "llm_output_max_tokens")
                    )
                    max_prompt_tokens = self._resolve_positive_limit(
                        get_tier_limit(tenant_tier, "llm_prompt_max_input_tokens"),
                        minimum=256,
                        maximum=131_072,
                    )

                    prompt_tokens = max(500, len(usage_summary_to_analyze.records) * 20)
                    if max_prompt_tokens is not None:
                        prompt_tokens = min(prompt_tokens, max_prompt_tokens)
                    completion_tokens = max_output_tokens or 500

                    reserved_amount = await LLMBudgetManager.check_and_reserve(
                        tenant_id=tenant_id,
                        db=effective_db,
                        model=effective_model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        operation_id=operation_id,
                        user_id=user_id,
                        actor_type=actor_type,
                        client_ip=client_ip,
                    )

                    logger.info(
                        "llm_budget_authorized",
                        tenant_id=str(tenant_id),
                        reserved_amount=float(reserved_amount),
                        operation_id=operation_id,
                    )
            except BudgetExceededError:
                raise
            except (
                SQLAlchemyError,
                RuntimeError,
                ValueError,
                TypeError,
                OSError,
            ) as exc:  # noqa: BLE001
                logger.error(
                    "budget_check_failed_unexpected",
                    error=str(exc),
                    operation_id=operation_id,
                )
                raise AIAnalysisError(f"Budget verification failed: {str(exc)}") from exc

            try:
                sanitized_data = await LLMGuardrails.sanitize_input(
                    usage_summary_to_analyze.model_dump()
                )
                sanitized_data["symbolic_forecast"] = await SymbolicForecaster.forecast(
                    usage_summary_to_analyze.records,
                    db=effective_db,
                    tenant_id=tenant_id,
                )
                formatted_data = json.dumps(sanitized_data, default=str)
            except (
                AIAnalysisError,
                ValueError,
                TypeError,
                RuntimeError,
            ) as exc:  # noqa: BLE001
                logger.error("data_preparation_failed", error=str(exc), operation_id=operation_id)
                raise AIAnalysisError(f"Failed to prepare data: {str(exc)}")

            effective_provider, final_model, byok_key = await self._setup_client_and_usage(
                tenant_id,
                effective_db,
                provider,
                effective_model,
                input_text=formatted_data,
            )
            try:
                response_content, response_metadata = await self._invoke_llm(
                    formatted_data,
                    effective_provider,
                    final_model,
                    byok_key,
                    max_output_tokens=max_output_tokens,
                    tenant_tier=tenant_tier,
                )
            except (AIAnalysisError, RuntimeError, ValueError, TypeError) as exc:
                logger.error("llm_invocation_failed", error=str(exc), operation_id=operation_id)
                raise

            if reserved_amount and effective_db:
                try:
                    token_usage = response_metadata.get("token_usage", {})
                    tenant_id_for_usage = cast(UUID, tenant_id)
                    await LLMBudgetManager.record_usage(
                        tenant_id=tenant_id_for_usage,
                        db=effective_db,
                        model=final_model,
                        provider=effective_provider,
                        prompt_tokens=token_usage.get("prompt_tokens", 500),
                        completion_tokens=token_usage.get("completion_tokens", 500),
                        is_byok=bool(byok_key),
                        operation_id=operation_id,
                        user_id=user_id,
                        actor_type=actor_type,
                        client_ip=client_ip,
                    )
                except (SQLAlchemyError, RuntimeError, ValueError, TypeError) as exc:
                    logger.warning(
                        "usage_recording_failed",
                        error=str(exc),
                        operation_id=operation_id,
                    )

            return await self._process_analysis_results(
                response_content,
                tenant_id,
                usage_summary_to_analyze,
                db=effective_db,
                provider=effective_provider,
                model=final_model,
                response_metadata=response_metadata,
            )

    async def _check_cache_and_delta(
        self,
        tenant_id: Optional[UUID],
        force_refresh: bool,
        usage_summary: Any,
    ) -> tuple[dict[str, Any] | None, bool]:
        from app.schemas.costs import CostRecord

        return await check_cache_and_delta(
            tenant_id=tenant_id,
            force_refresh=force_refresh,
            usage_summary=usage_summary,
            get_cache_service_fn=get_cache_service,
            get_settings_fn=get_settings,
            cost_record_cls=CostRecord,
            logger_obj=logger,
        )

    async def _setup_client_and_usage(
        self,
        tenant_id: Optional[UUID],
        db: Optional[AsyncSession],
        provider: Optional[str],
        model: Optional[str],
        input_text: Optional[str] = None,
    ) -> tuple[str, str, Optional[str]]:
        _ = input_text
        return await setup_client_and_usage(
            tenant_id=tenant_id,
            db=db,
            provider=provider,
            model=model,
            budget_manager=LLMBudgetManager,
            llm_budget_model=LLMBudget,
            settings_provider=get_settings,
            logger_obj=logger,
        )

    async def _invoke_llm(
        self,
        formatted_data: str,
        provider: str,
        model: str,
        byok_key: Optional[str],
        max_output_tokens: Optional[int] = None,
        tenant_tier: PricingTier | None = None,
    ) -> tuple[str, dict[str, Any]]:
        prompt_template = await self._get_prompt()
        return await invoke_llm(
            llm=self.llm,
            prompt_template=prompt_template,
            formatted_data=formatted_data,
            provider=provider,
            model=model,
            byok_key=byok_key,
            max_output_tokens=max_output_tokens,
            tenant_tier=tenant_tier,
            bind_output_token_ceiling=self._bind_output_token_ceiling,
            llm_factory=LLMFactory,
            settings_provider=get_settings,
            tracer_obj=tracer,
            logger_obj=logger,
        )

    async def _process_analysis_results(
        self,
        content: str,
        tenant_id: Optional[UUID],
        usage_summary: Any,
        db: Optional[AsyncSession] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        response_metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        effective_db = db or self.db
        return await process_analysis_results(
            content=content,
            tenant_id=tenant_id,
            usage_summary=usage_summary,
            db=effective_db,
            provider=provider,
            model=model,
            response_metadata=response_metadata,
            cache_service_factory=get_cache_service,
            validate_output_fn=LLMGuardrails.validate_output,
            finops_model=FinOpsAnalysisResult,
            forecast_fn=SymbolicForecaster.forecast,
            strip_markdown_fn=self._strip_markdown,
            normalize_analysis_payload_fn=self._normalize_analysis_payload,
            check_and_alert_anomalies_fn=self._check_and_alert_anomalies,
            prompt_version=self.prompt_version,
            schema_version=FINOPS_ANALYSIS_SCHEMA_VERSION,
            response_normalizer_version=FINOPS_RESPONSE_NORMALIZER_VERSION,
            logger_obj=logger,
        )

    async def _check_and_alert_anomalies(
        self,
        result: dict[str, Any],
        tenant_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None,
    ) -> None:
        await check_and_alert_anomalies(
            result=result,
            tenant_id=tenant_id,
            db=db,
            get_tenant_slack_service_fn=get_tenant_slack_service,
            get_slack_service_fn=get_slack_service,
            logger_obj=logger,
        )
