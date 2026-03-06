from typing import Any


def render_summary_csv(payload: Any) -> str:
    lines: list[str] = []
    lines.append(
        "provider,opportunity_monthly_usd,realized_monthly_usd,open_recommendations,applied_recommendations,pending_remediations,completed_remediations"
    )
    for item in payload.breakdown:
        lines.append(
            f"{item.provider},{item.opportunity_monthly_usd:.2f},{item.realized_monthly_usd:.2f},"
            f"{item.open_recommendations},{item.applied_recommendations},"
            f"{item.pending_remediations},{item.completed_remediations}"
        )
    lines.append("")
    lines.append(
        f"TOTAL,{payload.opportunity_monthly_usd:.2f},{payload.realized_monthly_usd:.2f},"
        f"{payload.open_recommendations},{payload.applied_recommendations},"
        f"{payload.pending_remediations},{payload.completed_remediations}"
    )
    return "\n".join(lines) + "\n"


def render_drilldown_csv(payload: Any) -> str:
    header = [
        payload.dimension,
        "opportunity_monthly_usd",
        "realized_monthly_usd",
        "open_recommendations",
        "applied_recommendations",
        "pending_remediations",
        "completed_remediations",
    ]
    lines = [",".join(header)]
    for item in payload.buckets:
        lines.append(
            ",".join(
                [
                    str(item.key),
                    f"{item.opportunity_monthly_usd:.2f}",
                    f"{item.realized_monthly_usd:.2f}",
                    str(item.open_recommendations),
                    str(item.applied_recommendations),
                    str(item.pending_remediations),
                    str(item.completed_remediations),
                ]
            )
        )
    lines.append("")
    lines.append(
        f"TOTAL,{payload.opportunity_monthly_usd:.2f},{payload.realized_monthly_usd:.2f},"
        f"{sum(bucket.open_recommendations for bucket in payload.buckets)},"
        f"{sum(bucket.applied_recommendations for bucket in payload.buckets)},"
        f"{sum(bucket.pending_remediations for bucket in payload.buckets)},"
        f"{sum(bucket.completed_remediations for bucket in payload.buckets)}"
    )
    return "\n".join(lines) + "\n"
