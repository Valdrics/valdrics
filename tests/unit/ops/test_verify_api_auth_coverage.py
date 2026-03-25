from __future__ import annotations

import os
import sys
from fastapi import APIRouter, FastAPI
from types import SimpleNamespace

from scripts.verify_api_auth_coverage import (
    collect_auth_coverage_violations,
    load_app_for_audit,
    main,
)


def test_collect_auth_coverage_detects_unprotected_private_route() -> None:
    app = FastAPI()
    router = APIRouter()

    @router.get("/private")
    async def private_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router, prefix="/api/v1/demo")

    violations = collect_auth_coverage_violations(app)
    assert len(violations) == 1
    assert violations[0].method == "GET"
    assert violations[0].path == "/api/v1/demo/private"


def test_collect_auth_coverage_exempts_only_known_public_routes() -> None:
    app = FastAPI()
    router = APIRouter()

    @router.post("/sso/discovery")
    async def public_status() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router, prefix="/api/v1/public")

    violations = collect_auth_coverage_violations(app)
    assert violations == []


def test_collect_auth_coverage_detects_unprotected_unknown_public_subpath() -> None:
    app = FastAPI()
    router = APIRouter()

    @router.get("/secret-admin-export")
    async def public_status() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router, prefix="/api/v1/public")

    violations = collect_auth_coverage_violations(app)
    assert len(violations) == 1
    assert violations[0].method == "GET"
    assert violations[0].path == "/api/v1/public/secret-admin-export"


def test_collect_auth_coverage_passes_current_application_routes() -> None:
    app = load_app_for_audit()
    violations = collect_auth_coverage_violations(app)
    assert violations == []


def test_main_returns_two_when_app_load_fails(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "scripts.verify_api_auth_coverage.load_app_for_audit",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    exit_code = main()

    captured = capsys.readouterr().out
    assert exit_code == 2
    assert "failed to load app" in captured


def test_load_app_for_audit_restores_environment(monkeypatch) -> None:
    monkeypatch.setenv("TESTING", "original-testing")
    monkeypatch.setenv("DEBUG", "original-debug")
    monkeypatch.setitem(
        sys.modules,
        "app.main",
        SimpleNamespace(app=FastAPI()),
    )

    app = load_app_for_audit()

    assert isinstance(app, FastAPI)
    assert os.environ["TESTING"] == "original-testing"
    assert os.environ["DEBUG"] == "original-debug"
