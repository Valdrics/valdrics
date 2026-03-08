from __future__ import annotations

import json

import pytest

import scripts.run_disaster_recovery_drill as run_disaster_recovery_drill


@pytest.mark.asyncio
async def test_request_json_returns_parsed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"status": "ok"}

    class Client:
        async def request(self, method, url, headers=None, json=None):
            return Response()

    status, payload = await run_disaster_recovery_drill._request_json(
        Client(), "GET", "http://127.0.0.1:8000/health/live"
    )

    assert status == 200
    assert payload == {"status": "ok"}


@pytest.mark.asyncio
async def test_request_json_falls_back_to_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 503
        text = "service unavailable"

        @staticmethod
        def json():
            raise ValueError("not json")

    class Client:
        async def request(self, method, url, headers=None, json=None):
            return Response()

    status, payload = await run_disaster_recovery_drill._request_json(
        Client(), "GET", "http://127.0.0.1:8000/health"
    )

    assert status == 503
    assert payload == "service unavailable"


@pytest.mark.asyncio
async def test_main_records_duration_and_enforces_max_duration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_path = tmp_path / "dr.json"
    monkeypatch.setattr(
        run_disaster_recovery_drill,
        "_parse_args",
        lambda: type(
            "Args",
            (),
            {
                "url": "http://127.0.0.1:8000",
                "out": str(out_path),
                "max_duration_seconds": 10,
            },
        )(),
    )
    monkeypatch.setattr(
        run_disaster_recovery_drill,
        "create_access_token",
        lambda *_args, **_kwargs: "token",
    )

    class Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, headers=None, json=None):
            del method, headers, json

            class Response:
                status_code = 200

                @staticmethod
                def json():
                    return {"url": url, "ok": True}

            return Response()

    monkeypatch.setattr(run_disaster_recovery_drill.httpx, "AsyncClient", Client)

    await run_disaster_recovery_drill.main()

    captured = json.loads(capsys.readouterr().out)
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert captured["duration_seconds"] >= 0
    assert captured["rebuild_and_verify_objective_seconds"] == 10
    assert captured["regional_recovery_mode"] == "manual_restore_redeploy_reroute"
    assert captured["regional_recovery_rto_seconds"] == 10
    assert (
        captured["regional_recovery_rpo_contract"]
        == "provider_backup_restore_external_to_repository"
    )
    assert captured["regional_recovery_rehearsal_cadence"] == "monthly"
    assert (
        captured["regional_recovery_contract_scope"]
        == "repository_managed_application_surface"
    )
    assert written["duration_seconds"] == captured["duration_seconds"]
    assert written["started_at"] <= written["captured_at"]


@pytest.mark.asyncio
async def test_main_fails_when_duration_exceeds_objective(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        run_disaster_recovery_drill,
        "_parse_args",
        lambda: type(
            "Args",
            (),
            {
                "url": "http://127.0.0.1:8000",
                "out": "",
                "max_duration_seconds": 1,
            },
        )(),
    )
    monkeypatch.setattr(
        run_disaster_recovery_drill,
        "create_access_token",
        lambda *_args, **_kwargs: "token",
    )

    class Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, headers=None, json=None):
            del method, url, headers, json

            class Response:
                status_code = 200

                @staticmethod
                def json():
                    return {"ok": True}

            return Response()

    perf_counter_values = iter((100.0, 102.5))
    monkeypatch.setattr(run_disaster_recovery_drill.httpx, "AsyncClient", Client)
    monkeypatch.setattr(
        run_disaster_recovery_drill.time,
        "perf_counter",
        lambda: next(perf_counter_values),
    )

    with pytest.raises(SystemExit, match="exceeded rebuild-and-verify objective"):
        await run_disaster_recovery_drill.main()
