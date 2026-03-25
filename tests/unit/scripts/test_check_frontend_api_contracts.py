from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

from scripts import check_frontend_api_contracts as script_module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_path_matches_exact_path() -> None:
    assert script_module.path_matches(
        "/api/v1/settings/connections/aws",
        "/api/v1/settings/connections/aws",
    )


def test_path_matches_backend_template_segment() -> None:
    assert script_module.path_matches(
        "/api/v1/settings/connections/aws/123/verify",
        "/api/v1/settings/connections/aws/{connection_id}/verify",
    )


def test_path_matches_frontend_template_segment() -> None:
    assert script_module.path_matches(
        "/api/v1/settings/connections/{param}/{param}/verify",
        "/api/v1/settings/connections/azure/{connection_id}/verify",
    )


def test_path_matches_supports_path_catchall_segments() -> None:
    assert script_module.path_matches(
        "/api/edge/api/v1/costs?start=2026-01-01".split("?", 1)[0],
        "/api/edge/{path:path}",
    )


def test_path_matches_rejects_different_path_shape() -> None:
    assert not script_module.path_matches(
        "/api/v1/settings/connections/{param}",
        "/api/v1/settings/connections/aws/{connection_id}/verify",
    )


def test_parse_frontend_paths_includes_direct_base_api_refs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(
        repo_root / "dashboard/src/lib/components/LandingHero.svelte",
        """
        <script lang="ts">
            import { base } from '$app/paths';
            const GEO_CURRENCY_HINT_ENDPOINT = `${base}/api/geo/currency`;
        </script>
        <div>{`GET ${base}/api/edge/api/v1/costs`}</div>
        """,
    )

    refs = script_module.parse_frontend_paths(repo_root)
    paths = {ref.path for ref in refs}

    assert "/api/geo/currency" in paths
    assert "/api/edge/api/v1/costs" not in paths


def test_parse_dashboard_server_paths_discovers_local_api_routes(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / "dashboard/src/routes/api/geo/currency/+server.ts", "export const GET = () => {};")
    _write(repo_root / "dashboard/src/routes/api/edge/[...path]/+server.ts", "export const GET = () => {};")

    declared_paths = script_module.parse_dashboard_server_paths(repo_root)

    assert "/api/geo/currency" in declared_paths
    assert "/api/edge/{path:path}" in declared_paths


def test_run_accepts_frontend_refs_backed_by_local_dashboard_routes(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / "dashboard/src/routes/api/geo/currency/+server.ts", "export const GET = () => {};")
    _write(
        repo_root / "dashboard/src/routes/roi-planner/+page.svelte",
        """
        <script lang="ts">
            import { base } from '$app/paths';
            const GEO_CURRENCY_HINT_ENDPOINT = `${base}/api/geo/currency`;
        </script>
        """,
    )
    monkeypatch.setattr(script_module, "parse_backend_paths", lambda _: set())

    assert script_module.run(repo_root) == 0
    assert "OK" in capsys.readouterr().out


def test_run_flags_missing_direct_api_refs(tmp_path: Path, monkeypatch, capsys) -> None:
    repo_root = tmp_path / "repo"
    _write(
        repo_root / "dashboard/src/routes/roi-planner/+page.svelte",
        """
        <script lang="ts">
            import { base } from '$app/paths';
            const GEO_CURRENCY_HINT_ENDPOINT = `${base}/api/geo/currency`;
        </script>
        """,
    )
    monkeypatch.setattr(script_module, "parse_backend_paths", lambda _: set())

    assert script_module.run(repo_root) == 1
    assert "/api/geo/currency" in capsys.readouterr().out


def test_main_resolves_relative_repo_root_from_repo_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = Path(script_module.__file__).resolve().parents[1]
    captured: dict[str, Path] = {}

    def _capture(repo_root: Path) -> int:
        captured["repo_root"] = repo_root
        return 0

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(script_module, "run", _capture)

    assert script_module.main(["--repo-root", "."]) == 0
    assert captured["repo_root"] == repo_root


def test_main_rejects_relative_repo_root_escape(capsys) -> None:
    assert script_module.main(["--repo-root", os.path.join("..", "..")]) == 2
    assert "repo_root must stay within repo root when relative" in capsys.readouterr().out


def test_parse_backend_paths_restores_env_and_sys_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    original_testing = os.environ.get("TESTING")
    sentinel_path = str(tmp_path / "sentinel")
    sys.path.append(sentinel_path)

    monkeypatch.setitem(
        sys.modules,
        "app.main",
        SimpleNamespace(app=SimpleNamespace(routes=[])),
    )

    script_module.parse_backend_paths(repo_root)

    assert os.environ.get("TESTING") == original_testing
    assert sys.path.count(str(repo_root)) == 0
    assert sys.path[-1] == sentinel_path
    sys.path.remove(sentinel_path)
