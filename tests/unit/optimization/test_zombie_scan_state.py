from __future__ import annotations

from app.modules.optimization.domain.zombie_scan_state import ZombieScanState


def test_merge_scan_results_preserves_degraded_scan_metadata() -> None:
    state = ZombieScanState.create(
        scanned_connections=1,
        has_precision=True,
        has_attribution=True,
    )

    state.merge_scan_results(
        provider_name="aws",
        connection_id="conn-1",
        connection_name="primary-account",
        region_override="us-east-1",
        scan_results={
            "idle_instances": [],
            "scan_completeness": {
                "provider": "aws",
                "region": "us-east-1",
                "degraded": True,
                "error_count": 1,
                "overall_error": None,
                "plugins": {
                    "idle_instances": {
                        "status": "timeout",
                        "error": "Plugin scan timed out",
                        "error_type": "TimeoutError",
                        "item_count": 0,
                        "validated_item_count": 0,
                    }
                },
            },
        },
    )

    assert state.payload["partial_results"] is True
    assert state.payload["scan_completeness"][0]["degraded"] is True
    assert state.payload["errors"][0]["category"] == "idle_instances"
    assert state.payload["errors"][0]["status"] == "timeout"


def test_merge_scan_results_preserves_top_level_scan_error() -> None:
    state = ZombieScanState.create(
        scanned_connections=1,
        has_precision=True,
        has_attribution=True,
    )

    state.merge_scan_results(
        provider_name="aws",
        connection_id="conn-2",
        connection_name="secondary-account",
        scan_results={
            "idle_instances": [],
            "region": "global",
            "error": "provider failed hard",
        },
    )

    assert state.payload["partial_results"] is True
    assert state.payload["errors"][0]["category"] == "scan"
    assert state.payload["errors"][0]["error"] == "provider failed hard"
