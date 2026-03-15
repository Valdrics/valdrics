from __future__ import annotations

from pathlib import Path

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
