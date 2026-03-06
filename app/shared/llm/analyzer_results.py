from __future__ import annotations

import json
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


async def check_and_alert_anomalies(
    *,
    result: dict[str, Any],
    tenant_id: UUID | None = None,
    db: AsyncSession | None = None,
    get_tenant_slack_service_fn: Callable[[AsyncSession, UUID], Awaitable[Any]],
    get_slack_service_fn: Callable[[], Any],
    logger_obj: Any,
) -> None:
    """Send Slack alert for top anomaly when configured."""
    anomalies = result.get("anomalies", [])
    if not anomalies:
        return

    try:
        if tenant_id:
            if db is None:
                logger_obj.warning(
                    "anomaly_alert_skipped_missing_tenant_db_context",
                    tenant_id=str(tenant_id),
                )
                return
            slack = await get_tenant_slack_service_fn(db, tenant_id)
        else:
            slack = get_slack_service_fn()

        if not slack:
            return

        top = anomalies[0]
        await slack.send_alert(
            title=f"Cost Anomaly Detected: {top['resource']}",
            message=(
                f"*Issue:* {top['issue']}\n"
                f"*Impact:* {top['cost_impact']}\n"
                f"*Severity:* {top['severity']}"
            ),
            severity="critical" if top["severity"] == "high" else "warning",
        )
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        logger_obj.warning(
            "anomaly_alert_dispatch_failed",
            tenant_id=str(tenant_id) if tenant_id else None,
            error=str(exc),
        )


async def process_analysis_results(
    *,
    content: str,
    tenant_id: UUID | None,
    usage_summary: Any,
    db: AsyncSession | None,
    provider: str | None,
    model: str | None,
    response_metadata: dict[str, Any] | None,
    cache_service_factory: Callable[[], Any],
    validate_output_fn: Callable[[str, Any], Any],
    finops_model: Any,
    forecast_fn: Callable[..., Awaitable[Any]],
    strip_markdown_fn: Callable[[str], str],
    normalize_analysis_payload_fn: Callable[[dict[str, Any]], dict[str, Any]],
    check_and_alert_anomalies_fn: Callable[..., Awaitable[None]],
    prompt_version: str,
    schema_version: str,
    response_normalizer_version: str,
    logger_obj: Any,
) -> dict[str, Any]:
    """Validate/normalize LLM output, enrich with symbolic forecast, and cache."""
    cache = cache_service_factory()

    try:
        validated = validate_output_fn(content, finops_model)
        llm_result = validated.model_dump()

        await check_and_alert_anomalies_fn(
            result=llm_result,
            tenant_id=tenant_id,
            db=db,
        )
    except (ValueError, TypeError, RuntimeError, KeyError) as exc:  # noqa: BLE001
        logger_obj.warning("llm_validation_failed", error=str(exc))
        try:
            llm_result = json.loads(strip_markdown_fn(content))
        except json.JSONDecodeError as parse_exc:
            logger_obj.error(
                "llm_fallback_json_parse_failed",
                error=str(parse_exc),
                content_snippet=content[:100],
            )
            llm_result = {
                "error": "AI analysis format invalid",
                "raw_content": content,
            }
        except (ValueError, TypeError, RuntimeError) as fallback_exc:
            logger_obj.error("llm_fallback_failed_unexpectedly", error=str(fallback_exc))
            llm_result = {
                "error": "AI analysis processing failed",
                "raw_content": content,
            }

    if not isinstance(llm_result, dict):
        llm_result = {
            "error": "AI analysis produced non-object payload",
            "raw_content": llm_result,
        }

    symbolic_forecast = await forecast_fn(
        usage_summary.records,
        db=db,
        tenant_id=usage_summary.tenant_id,
    )
    normalized = normalize_analysis_payload_fn(llm_result)

    metadata_keys: list[str] = []
    if isinstance(response_metadata, dict):
        metadata_keys = sorted(str(key) for key in response_metadata.keys())

    final_result = {
        "insights": normalized["insights"],
        "recommendations": normalized["recommendations"],
        "anomalies": normalized["anomalies"],
        "forecast": normalized["forecast"],
        "symbolic_forecast": symbolic_forecast,
        "llm_raw": llm_result,
        "analysis_contract": {
            "schema_version": schema_version,
            "prompt_version": prompt_version,
            "response_normalizer_version": response_normalizer_version,
            "provider": provider or "unknown",
            "model": model or "unknown",
            "llm_response_metadata_keys": metadata_keys,
        },
    }

    if tenant_id:
        await cache.set_analysis(tenant_id, final_result)
        logger_obj.info("analysis_cached", tenant_id=str(tenant_id))

    return final_result
