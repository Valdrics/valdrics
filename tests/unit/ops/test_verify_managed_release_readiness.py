from __future__ import annotations

from pathlib import Path
import subprocess

import scripts.verify_managed_release_readiness as managed_release_readiness
from scripts.verify_managed_release_readiness import (
    main,
    verify_managed_release_readiness,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_reports(root: Path, environment: str = "staging") -> tuple[Path, Path, Path]:
    runtime_report = root / ".runtime" / f"{environment}.report.json"
    migration_report = root / ".runtime" / f"{environment}.migrate.report.json"
    deployment_report = root / ".runtime" / "deploy" / environment / "deployment.report.json"
    _write(runtime_report, "{}\n")
    _write(migration_report, "{}\n")
    _write(deployment_report, "{}\n")
    return runtime_report, migration_report, deployment_report


def test_verify_managed_release_readiness_runs_all_requested_gates(tmp_path: Path) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)
    calls: list[tuple[str, object]] = []

    def _dashboard_runtime_verifier(*, root: Path, build: bool) -> list[str]:
        calls.append(("dashboard", (root, build)))
        return []

    def _bundle_verifier(
        *,
        environment: str,
        runtime_report_path: Path,
        migration_report_path: Path,
        deployment_report_path: Path,
    ) -> list[str]:
        calls.append(
            (
                "bundle",
                (
                    environment,
                    runtime_report_path,
                    migration_report_path,
                    deployment_report_path,
                ),
            )
        )
        return []

    def _public_quality_runner(*, dashboard_url: str | None, skip_webserver: bool, **_: object) -> None:
        calls.append(("public", (dashboard_url, skip_webserver)))

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        dashboard_url="https://staging.example.com",
        skip_webserver=True,
        dashboard_runtime_verifier=_dashboard_runtime_verifier,
        bundle_verifier=_bundle_verifier,
        public_quality_runner=_public_quality_runner,
    )

    assert errors == []
    assert ("dashboard", (tmp_path, True)) in calls
    assert (
        "bundle",
        ("staging", runtime_report, migration_report, deployment_report),
    ) in calls
    assert ("public", ("https://staging.example.com", True)) in calls


def test_verify_managed_release_readiness_requires_reuse_mode_for_local_preview(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        dashboard_url="http://127.0.0.1:4173",
        skip_webserver=True,
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=lambda **_: [],
        public_quality_runner=lambda **_: None,
    )

    assert errors == [
        "reuse_built_dashboard_runtime is required when using --skip-webserver "
        "with a local dashboard_url because rebuilding invalidates the live preview assets."
    ]


def test_verify_managed_release_readiness_requires_dashboard_url_when_public_gate_enabled(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        skip_dashboard_runtime=True,
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=lambda **_: [],
        public_quality_runner=lambda **_: None,
    )

    assert errors == ["dashboard_url is required unless --skip-public-browser is used."]


def test_verify_managed_release_readiness_reports_public_gate_failure(tmp_path: Path) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)

    def _failing_public_quality_runner(**_: object) -> None:
        raise subprocess.CalledProcessError(
            1,
            ["pnpm", "--dir", "dashboard", "run", "test:a11y:public"],
        )

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        dashboard_url="https://staging.example.com",
        skip_dashboard_runtime=True,
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=lambda **_: [],
        public_quality_runner=_failing_public_quality_runner,
    )

    assert len(errors) == 1
    assert "public frontend quality gate failed" in errors[0]


def test_verify_managed_release_readiness_reuses_existing_build_when_requested(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)
    calls: list[tuple[str, object]] = []

    def _dashboard_runtime_verifier(*, root: Path, build: bool) -> list[str]:
        calls.append(("dashboard", (root, build)))
        return []

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        dashboard_url="http://127.0.0.1:4173",
        skip_webserver=True,
        reuse_built_dashboard_runtime=True,
        dashboard_runtime_verifier=_dashboard_runtime_verifier,
        bundle_verifier=lambda **_: [],
        public_quality_runner=lambda **_: None,
    )

    assert errors == []
    assert ("dashboard", (tmp_path, False)) in calls


def test_main_reports_success_and_failure(tmp_path: Path, capsys) -> None:
    managed_release_readiness.verify_managed_release_readiness = lambda **_: []
    assert main(["--environment", "staging", "--root", str(tmp_path)]) == 0
    assert "[managed-release-readiness] ok" in capsys.readouterr().out

    managed_release_readiness.verify_managed_release_readiness = (
        lambda **_: ["dashboard_url is required unless --skip-public-browser is used."]
    )
    assert main(["--environment", "staging", "--root", str(tmp_path)]) == 1
    assert "[managed-release-readiness] FAILED" in capsys.readouterr().out
