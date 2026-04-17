from __future__ import annotations

import json
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
    deployment_report = (
        root / ".runtime" / "deploy" / environment / "deployment.report.json"
    )
    runtime_env = root / ".runtime" / f"{environment}.env"
    _write(runtime_env, "FRONTEND_URL=\n")
    _write(
        runtime_report,
        json.dumps(
            {
                "output_path": str(runtime_env),
                "resolved_public_runtime_values": {
                    "API_URL": "",
                    "FRONTEND_URL": "",
                },
            },
            indent=2,
        )
        + "\n",
    )
    _write(migration_report, "{}\n")
    _write(deployment_report, "{}\n")
    return runtime_report, migration_report, deployment_report


def test_verify_managed_release_readiness_runs_all_requested_gates(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)
    calls: list[tuple[str, object]] = []

    def _audit_report_verifier(
        *, root: Path, report_path: Path, enforce_live_measured_facts: bool
    ) -> list[str]:
        calls.append(("audit", (root, report_path, enforce_live_measured_facts)))
        return []

    def _dashboard_runtime_verifier(*, root: Path, build: bool) -> list[str]:
        calls.append(("dashboard", (root, build)))
        return []

    def _bundle_verifier(
        *,
        environment: str,
        runtime_report_path: Path,
        migration_report_path: Path,
        deployment_report_path: Path,
        allow_non_secret_artifact_bundle: bool,
    ) -> list[str]:
        calls.append(
            (
                "bundle",
                (
                    environment,
                    runtime_report_path,
                    migration_report_path,
                    deployment_report_path,
                    allow_non_secret_artifact_bundle,
                ),
            )
        )
        return []

    def _public_quality_runner(
        *, dashboard_url: str | None, skip_webserver: bool, **_: object
    ) -> None:
        calls.append(("public", (dashboard_url, skip_webserver)))

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        dashboard_url="https://staging.example.com",
        skip_webserver=True,
        audit_report_verifier=_audit_report_verifier,
        dashboard_runtime_verifier=_dashboard_runtime_verifier,
        bundle_verifier=_bundle_verifier,
        public_quality_runner=_public_quality_runner,
    )

    assert errors == []
    assert (
        "audit",
        (tmp_path, tmp_path / ".runtime/staging.audit.report.json", True),
    ) in calls
    assert ("dashboard", (tmp_path, True)) in calls
    assert (
        "bundle",
        ("staging", runtime_report, migration_report, deployment_report, False),
    ) in calls
    assert ("public", ("https://staging.example.com", True)) in calls


def test_verify_managed_release_readiness_can_verify_non_secret_release_artifact_bundle(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)
    calls: list[tuple[str, object]] = []

    def _bundle_verifier(
        *,
        environment: str,
        runtime_report_path: Path,
        migration_report_path: Path,
        deployment_report_path: Path,
        allow_non_secret_artifact_bundle: bool,
    ) -> list[str]:
        calls.append(
            (
                "bundle",
                (
                    environment,
                    runtime_report_path,
                    migration_report_path,
                    deployment_report_path,
                    allow_non_secret_artifact_bundle,
                ),
            )
        )
        return []

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        skip_dashboard_runtime=True,
        skip_public_browser=True,
        allow_non_secret_artifact_bundle=True,
        audit_report_verifier=lambda **_: [],
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=_bundle_verifier,
        public_quality_runner=lambda **_: None,
    )

    assert errors == []
    assert (
        "bundle",
        ("staging", runtime_report, migration_report, deployment_report, True),
    ) in calls


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
        audit_report_verifier=lambda **_: [],
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
        audit_report_verifier=lambda **_: [],
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=lambda **_: [],
        public_quality_runner=lambda **_: None,
    )

    assert errors == [
        "dashboard_url is required unless --skip-public-browser is used, or "
        "FRONTEND_URL is set to a live http(s) value in the managed runtime env."
    ]


def test_verify_managed_release_readiness_derives_dashboard_url_from_runtime_env(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)
    runtime_env = tmp_path / ".runtime" / "staging.env"
    _write(runtime_env, "FRONTEND_URL=https://derived.example.com\n")
    calls: list[tuple[str, object]] = []

    def _public_quality_runner(
        *, dashboard_url: str | None, skip_webserver: bool, **_: object
    ) -> None:
        calls.append(("public", (dashboard_url, skip_webserver)))

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        skip_dashboard_runtime=True,
        audit_report_verifier=lambda **_: [],
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=lambda **_: [],
        public_quality_runner=_public_quality_runner,
    )

    assert errors == []
    assert ("public", ("https://derived.example.com", False)) in calls


def test_verify_managed_release_readiness_prefers_runtime_report_public_values(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)
    runtime_payload = json.loads(runtime_report.read_text(encoding="utf-8"))
    runtime_payload["resolved_public_runtime_values"]["FRONTEND_URL"] = (
        "https://report.example.com"
    )
    _write(runtime_report, json.dumps(runtime_payload, indent=2) + "\n")
    calls: list[tuple[str, object]] = []

    def _public_quality_runner(
        *, dashboard_url: str | None, skip_webserver: bool, **_: object
    ) -> None:
        calls.append(("public", (dashboard_url, skip_webserver)))

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        skip_dashboard_runtime=True,
        audit_report_verifier=lambda **_: [],
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=lambda **_: [],
        public_quality_runner=_public_quality_runner,
    )

    assert errors == []
    assert ("public", ("https://report.example.com", False)) in calls


def test_verify_managed_release_readiness_reports_public_gate_failure(
    tmp_path: Path,
) -> None:
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
        audit_report_verifier=lambda **_: [],
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=lambda **_: [],
        public_quality_runner=_failing_public_quality_runner,
    )

    assert len(errors) == 1
    assert "public frontend quality gate failed" in errors[0]


def test_verify_managed_release_readiness_reports_dashboard_gate_exception(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        dashboard_url="https://staging.example.com",
        audit_report_verifier=lambda **_: [],
        dashboard_runtime_verifier=lambda **_: (_ for _ in ()).throw(
            PermissionError("port bind denied")
        ),
        bundle_verifier=lambda **_: [],
        public_quality_runner=lambda **_: None,
    )

    assert (
        "dashboard runtime contract verification failed unexpectedly: port bind denied"
        in errors
    )


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
        audit_report_verifier=lambda **_: [],
        dashboard_runtime_verifier=_dashboard_runtime_verifier,
        bundle_verifier=lambda **_: [],
        public_quality_runner=lambda **_: None,
    )

    assert errors == []
    assert ("dashboard", (tmp_path, False)) in calls


def test_verify_managed_release_readiness_reports_audit_gate_failures(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(tmp_path)

    errors = verify_managed_release_readiness(
        environment="staging",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        dashboard_url="https://staging.example.com",
        skip_dashboard_runtime=True,
        audit_report_verifier=lambda **_: ["audit drift detected"],
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=lambda **_: [],
        public_quality_runner=lambda **_: None,
    )

    assert "audit drift detected" in errors


def test_verify_managed_release_readiness_uses_environment_specific_audit_report(
    tmp_path: Path,
) -> None:
    runtime_report, migration_report, deployment_report = _seed_reports(
        tmp_path,
        environment="production",
    )
    calls: list[tuple[str, object]] = []

    def _audit_report_verifier(
        *, root: Path, report_path: Path, enforce_live_measured_facts: bool
    ) -> list[str]:
        calls.append(("audit", (root, report_path, enforce_live_measured_facts)))
        return []

    errors = verify_managed_release_readiness(
        environment="production",
        root=tmp_path,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        dashboard_url="https://production.example.com",
        skip_dashboard_runtime=True,
        audit_report_verifier=_audit_report_verifier,
        dashboard_runtime_verifier=lambda **_: [],
        bundle_verifier=lambda **_: [],
        public_quality_runner=lambda **_: None,
    )

    assert errors == []
    assert (
        "audit",
        (tmp_path, tmp_path / ".runtime/production.audit.report.json", True),
    ) in calls


def test_main_reports_success_and_failure(tmp_path: Path, capsys) -> None:
    managed_release_readiness.verify_managed_release_readiness = lambda **_: []
    assert main(["--environment", "staging", "--root", str(tmp_path)]) == 0
    assert "[managed-release-readiness] ok" in capsys.readouterr().out

    managed_release_readiness.verify_managed_release_readiness = lambda **_: [
        "dashboard_url is required unless --skip-public-browser is used, or "
        "FRONTEND_URL is set to a live http(s) value in the managed runtime env."
    ]
    assert main(["--environment", "staging", "--root", str(tmp_path)]) == 1
    assert "[managed-release-readiness] FAILED" in capsys.readouterr().out
