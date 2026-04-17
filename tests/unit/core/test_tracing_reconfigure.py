from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import app.shared.core.tracing as tracing_module


def _settings(
    *,
    project_id: str | None,
    environment: str = "development",
    testing: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        TESTING=testing,
        GCP_PROJECT_ID=project_id,
        ENVIRONMENT=environment,
    )


def setup_function() -> None:
    tracing_module._configured_tracer_provider = None
    tracing_module._configured_tracing_signature = None


def teardown_function() -> None:
    tracing_module._configured_tracer_provider = None
    tracing_module._configured_tracing_signature = None


def test_setup_tracing_reconfigures_existing_provider_when_project_changes() -> None:
    provider = MagicMock()
    fake_cloud_trace_module = types.SimpleNamespace(
        CloudTraceSpanExporter=MagicMock(side_effect=[MagicMock(), MagicMock()])
    )

    with (
        patch("app.shared.core.tracing.get_settings") as get_settings,
        patch.dict(
            sys.modules,
            {"opentelemetry.exporter.cloud_trace": fake_cloud_trace_module},
        ),
        patch(
            "app.shared.core.tracing.TracerProvider", return_value=provider
        ) as provider_cls,
        patch("app.shared.core.tracing.trace.set_tracer_provider") as set_provider,
        patch(
            "app.shared.core.tracing.BatchSpanProcessor",
            side_effect=lambda exporter: ("processor", exporter),
        ) as batch_processor,
    ):
        get_settings.return_value = _settings(
            project_id="valdrics-a",
            environment="production",
        )
        tracing_module.setup_tracing()

        get_settings.return_value = _settings(
            project_id="valdrics-b",
            environment="production",
        )
        tracing_module.setup_tracing()

    provider_cls.assert_called_once()
    set_provider.assert_called_once_with(provider)
    assert provider.shutdown.call_count == 1
    assert provider.add_span_processor.call_count == 2
    assert fake_cloud_trace_module.CloudTraceSpanExporter.call_args_list[0].kwargs == {
        "project_id": "valdrics-a",
    }
    assert fake_cloud_trace_module.CloudTraceSpanExporter.call_args_list[1].kwargs == {
        "project_id": "valdrics-b",
    }
    assert batch_processor.call_count == 2
    assert tracing_module._configured_tracing_signature == ("valdrics-b", "production")


def test_setup_tracing_instruments_fastapi_app_only_once() -> None:
    provider = MagicMock()
    app = MagicMock()
    app.state = SimpleNamespace()

    with (
        patch(
            "app.shared.core.tracing.get_settings",
            return_value=_settings(project_id=None, environment="development"),
        ),
        patch("app.shared.core.tracing.TracerProvider", return_value=provider),
        patch("app.shared.core.tracing.trace.set_tracer_provider"),
        patch("app.shared.core.tracing.ConsoleSpanExporter"),
        patch(
            "app.shared.core.tracing.BatchSpanProcessor",
            side_effect=lambda exporter: ("processor", exporter),
        ),
        patch(
            "app.shared.core.tracing.FastAPIInstrumentor.instrument_app"
        ) as instrument_app,
    ):
        tracing_module.setup_tracing(app=app)
        tracing_module.setup_tracing(app=app)

    instrument_app.assert_called_once_with(app)
