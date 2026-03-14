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


def test_build_cloudflare_dns_payload_rejects_non_default_port() -> None:
    with pytest.raises(ValueError, match="non-default port"):
        run_regional_failover._build_cloudflare_dns_payload(
            record_name="api.valdrics.example",
            target_origin="https://secondary-api.valdrics.example:8443",
        )


def test_normalize_origin_rejects_path_suffix() -> None:
    with pytest.raises(ValueError, match="bare origin without path"):
        run_regional_failover._normalize_origin(
            "https://secondary-api.valdrics.example/ready"
        )


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
    assert captured["steps"]["health_ready"]["url"] == "https://api-dr.valdrics.example/health"
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
    monkeypatch.setenv(
        "FAILOVER_AWS_ROLE_TO_ASSUME",
        "arn:aws:iam::123456789012:role/github-actions-failover",
    )

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
    sts_client = SimpleNamespace(
        get_caller_identity=lambda: {
            "Account": "123456789012",
            "Arn": "arn:aws:sts::123456789012:assumed-role/github-actions-failover/regional-failover-123",
            "UserId": "AROAXYZ:regional-failover-123",
        }
    )
    monkeypatch.setattr(
        run_regional_failover,
        "_get_rds_client",
        lambda *, region_name: rds_client,
    )
    monkeypatch.setattr(
        run_regional_failover,
        "_get_sts_client",
        lambda *, region_name: sts_client,
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
                if url.endswith("/health/live"):
                    return Response(200, {"status": "ok"})
                assert url == "https://api-dr.valdrics.example/health"
                return Response(
                    200,
                    {
                        "status": "healthy",
                        "checks": {
                            "database": {"status": "up"},
                            "cache": {"status": "healthy"},
                            "background_jobs": {
                                "status": "healthy",
                                "worker_health": {
                                    "status": "healthy",
                                    "worker_count": 1,
                                    "workers": ["worker@dr"],
                                },
                            },
                        },
                    },
                )
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
    assert (
        captured["aws_execution_identity"]["assumed_role"]
        == "arn:aws:iam::123456789012:role/github-actions-failover"
    )
    assert captured["steps"]["health_live"]["status_code"] == 200
    assert captured["steps"]["health_ready"]["status_code"] == 200
    assert captured["steps"]["cutover_dns"]["status_code"] == 200


@pytest.mark.asyncio
async def test_main_blocks_cutover_when_readiness_is_not_dependency_healthy(
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setattr(
        run_regional_failover,
        "_get_rds_client",
        lambda *, region_name: SimpleNamespace(
            promote_read_replica=lambda **kwargs: None,
            describe_db_instances=lambda **kwargs: {
                "DBInstances": [
                    {
                        "DBInstanceArn": "arn:aws:rds:us-west-2:123:db:dr",
                        "DBInstanceStatus": "available",
                        "Engine": "postgres",
                        "Endpoint": {"Address": "db-dr.valdrics.internal"},
                    }
                ]
            },
        ),
    )
    monkeypatch.setattr(
        run_regional_failover,
        "_get_sts_client",
        lambda *, region_name: SimpleNamespace(
            get_caller_identity=lambda: {
                "Account": "123456789012",
                "Arn": "arn:aws:sts::123456789012:assumed-role/github-actions-failover/run",
                "UserId": "AROAXYZ:run",
            }
        ),
    )

    class Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, headers=None, json=None):
            del headers, json

            class Response:
                def __init__(self, status_code: int, payload: object) -> None:
                    self.status_code = status_code
                    self._payload = payload
                    self.text = str(payload)

                def json(self):
                    return self._payload

            if url.endswith("/health/live"):
                return Response(200, {"status": "ok"})
            return Response(
                200,
                {
                    "status": "degraded",
                    "checks": {
                        "database": {"status": "up"},
                        "cache": {"status": "healthy"},
                        "background_jobs": {
                            "status": "unknown",
                            "worker_health": {
                                "status": "degraded",
                                "worker_count": 0,
                                "workers": [],
                            },
                        },
                    },
                },
            )

    monkeypatch.setattr(run_regional_failover.httpx, "AsyncClient", Client)

    with pytest.raises(SystemExit, match="background job processing state"):
        await run_regional_failover.main()


@pytest.mark.asyncio
async def test_main_blocks_cutover_when_cloudflare_success_flag_is_false(
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setattr(
        run_regional_failover,
        "_get_rds_client",
        lambda *, region_name: SimpleNamespace(
            promote_read_replica=lambda **kwargs: None,
            describe_db_instances=lambda **kwargs: {
                "DBInstances": [
                    {
                        "DBInstanceArn": "arn:aws:rds:us-west-2:123:db:dr",
                        "DBInstanceStatus": "available",
                        "Engine": "postgres",
                        "Endpoint": {"Address": "db-dr.valdrics.internal"},
                    }
                ]
            },
        ),
    )
    monkeypatch.setattr(
        run_regional_failover,
        "_get_sts_client",
        lambda *, region_name: SimpleNamespace(
            get_caller_identity=lambda: {
                "Account": "123456789012",
                "Arn": "arn:aws:sts::123456789012:assumed-role/github-actions-failover/run",
                "UserId": "AROAXYZ:run",
            }
        ),
    )

    class Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, headers=None, json=None):
            del headers, json

            class Response:
                def __init__(self, status_code: int, payload: object) -> None:
                    self.status_code = status_code
                    self._payload = payload
                    self.text = str(payload)

                def json(self):
                    return self._payload

            if method == "GET" and url.endswith("/health/live"):
                return Response(200, {"status": "ok"})
            if method == "GET" and url.endswith("/health"):
                return Response(
                    200,
                    {
                        "status": "healthy",
                        "checks": {
                            "database": {"status": "up"},
                            "cache": {"status": "healthy"},
                            "background_jobs": {
                                "status": "healthy",
                                "worker_health": {
                                    "status": "healthy",
                                    "worker_count": 1,
                                    "workers": ["worker@dr"],
                                },
                            },
                        },
                    },
                )
            return Response(200, {"success": False, "errors": [{"message": "denied"}]})

    monkeypatch.setattr(run_regional_failover.httpx, "AsyncClient", Client)

    with pytest.raises(SystemExit, match="success=true"):
        await run_regional_failover.main()


@pytest.mark.asyncio
async def test_main_blocks_cutover_when_worker_heartbeat_is_missing(
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setattr(
        run_regional_failover,
        "_get_rds_client",
        lambda *, region_name: SimpleNamespace(
            promote_read_replica=lambda **kwargs: None,
            describe_db_instances=lambda **kwargs: {
                "DBInstances": [
                    {
                        "DBInstanceArn": "arn:aws:rds:us-west-2:123:db:dr",
                        "DBInstanceStatus": "available",
                        "Engine": "postgres",
                        "Endpoint": {"Address": "db-dr.valdrics.internal"},
                    }
                ]
            },
        ),
    )
    monkeypatch.setattr(
        run_regional_failover,
        "_get_sts_client",
        lambda *, region_name: SimpleNamespace(
            get_caller_identity=lambda: {
                "Account": "123456789012",
                "Arn": "arn:aws:sts::123456789012:assumed-role/github-actions-failover/run",
                "UserId": "AROAXYZ:run",
            }
        ),
    )

    class Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, headers=None, json=None):
            del headers, json

            class Response:
                def __init__(self, status_code: int, payload: object) -> None:
                    self.status_code = status_code
                    self._payload = payload
                    self.text = str(payload)

                def json(self):
                    return self._payload

            if url.endswith("/health/live"):
                return Response(200, {"status": "ok"})
            return Response(
                200,
                {
                    "status": "healthy",
                    "checks": {
                        "database": {"status": "up"},
                        "cache": {"status": "healthy"},
                        "background_jobs": {
                            "status": "healthy",
                            "worker_health": {
                                "status": "degraded",
                                "worker_count": 0,
                                "workers": [],
                            },
                        },
                    },
                },
            )

    monkeypatch.setattr(run_regional_failover.httpx, "AsyncClient", Client)

    with pytest.raises(SystemExit, match="worker heartbeat coverage"):
        await run_regional_failover.main()
