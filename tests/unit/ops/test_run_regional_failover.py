from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import scripts.run_regional_failover as run_regional_failover


def test_build_cloudflare_dns_payload_uses_origin_hostname() -> None:
    payload = run_regional_failover._build_cloudflare_dns_payload(
        record_name="api.valdrics.example",
        target_origin="https://secondary-api.valdrics.example",
    )

    assert payload == {
        "type": "CNAME",
        "name": "api.valdrics.example",
        "content": "secondary-api.valdrics.example",
        "ttl": 1,
        "proxied": True,
    }


@pytest.mark.asyncio
async def test_main_dry_run_emits_automated_failover_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_path = tmp_path / "regional_failover.json"
    monkeypatch.setattr(
        run_regional_failover,
        "_parse_args",
        lambda: SimpleNamespace(
            secondary_region="us-west-2",
            secondary_db_instance_id="valdrics-db-prod-dr-us-west-2",
            secondary_api_origin="https://api-dr.valdrics.example",
            api_record_name="api.valdrics.example",
            cloudflare_zone_id="zone-123",
            cloudflare_dns_record_id="record-123",
            out=str(out_path),
            max_promotion_wait_seconds=1800,
            dry_run=True,
        ),
    )

    await run_regional_failover.main()

    captured = json.loads(capsys.readouterr().out)
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert captured["regional_recovery_mode"] == "automated_secondary_region_failover"
    assert captured["dry_run"] is True
    assert captured["steps"]["promote_replica"]["mode"] == "dry_run"
    assert captured["steps"]["cutover_dns"]["target_origin"] == "https://api-dr.valdrics.example"
    assert written["duration_seconds"] == captured["duration_seconds"]


@pytest.mark.asyncio
async def test_main_promotes_replica_checks_health_and_updates_cloudflare(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        run_regional_failover,
        "_parse_args",
        lambda: SimpleNamespace(
            secondary_region="us-west-2",
            secondary_db_instance_id="valdrics-db-prod-dr-us-west-2",
            secondary_api_origin="https://api-dr.valdrics.example",
            api_record_name="api.valdrics.example",
            cloudflare_zone_id="zone-123",
            cloudflare_dns_record_id="record-123",
            out="",
            max_promotion_wait_seconds=1800,
            dry_run=False,
        ),
    )
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "cloudflare-api-token-1234567890")

    class FakeRdsClient:
        def __init__(self) -> None:
            self.promote_calls: list[str] = []

        def promote_read_replica(self, *, DBInstanceIdentifier: str) -> None:
            self.promote_calls.append(DBInstanceIdentifier)

        def describe_db_instances(self, *, DBInstanceIdentifier: str) -> dict[str, object]:
            return {
                "DBInstances": [
                    {
                        "DBInstanceArn": f"arn:aws:rds:us-west-2:123:db:{DBInstanceIdentifier}",
                        "DBInstanceStatus": "available",
                        "Engine": "postgres",
                        "Endpoint": {"Address": "db-dr.valdrics.internal"},
                    }
                ]
            }

    rds_client = FakeRdsClient()
    monkeypatch.setattr(
        run_regional_failover,
        "_get_rds_client",
        lambda *, region_name: rds_client,
    )

    class Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, headers=None, json=None):
            class Response:
                def __init__(self, status_code: int, payload: object) -> None:
                    self.status_code = status_code
                    self._payload = payload
                    self.text = str(payload)

                def json(self):
                    return self._payload

            if method == "GET":
                assert url == "https://api-dr.valdrics.example/health/live"
                return Response(200, {"status": "ok"})
            assert method == "PATCH"
            assert headers and headers["Authorization"].startswith("Bearer ")
            assert json == {
                "type": "CNAME",
                "name": "api.valdrics.example",
                "content": "api-dr.valdrics.example",
                "ttl": 1,
                "proxied": True,
            }
            return Response(200, {"success": True})

    monkeypatch.setattr(run_regional_failover.httpx, "AsyncClient", Client)

    await run_regional_failover.main()

    captured = json.loads(capsys.readouterr().out)
    assert rds_client.promote_calls == ["valdrics-db-prod-dr-us-west-2"]
    assert captured["steps"]["health_live"]["status_code"] == 200
    assert captured["steps"]["cutover_dns"]["status_code"] == 200
