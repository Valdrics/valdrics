from __future__ import annotations

import subprocess

from scripts.run_public_frontend_quality_gate import (
    build_public_quality_commands,
    run_public_frontend_quality_gate,
)


def test_build_public_quality_commands_includes_expected_suites() -> None:
    commands = build_public_quality_commands(
        include_a11y=True,
        include_perf=True,
        include_visual=True,
    )

    assert commands[0][0] == "public critical-path smoke"
    assert commands[0][1][-1] == "--reporter=line"
    assert any(label == "public accessibility gate" for label, _ in commands)
    assert any(label == "public performance gate" for label, _ in commands)
    assert any(label == "public visual gate" for label, _ in commands)


def test_run_public_frontend_quality_gate_applies_dashboard_url_and_skip_webserver() -> None:
    calls: list[tuple[list[str], dict[str, str]]] = []

    def _runner(
        cmd: list[str],
        *,
        cwd,
        env,
        check,
        text,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd is not None
        assert check is True
        assert text is True
        calls.append((cmd, env))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    run_public_frontend_quality_gate(
        dashboard_url="http://localhost:5174",
        skip_webserver=True,
        include_a11y=False,
        include_perf=True,
        include_visual=False,
        runner=_runner,
    )

    assert len(calls) == 2
    assert calls[0][1]["DASHBOARD_URL"] == "http://localhost:5174"
    assert calls[0][1]["PLAYWRIGHT_SKIP_WEBSERVER"] == "1"
    assert "test:a11y:public" not in " ".join(" ".join(cmd) for cmd, _ in calls)
    assert "test:visual" not in " ".join(" ".join(cmd) for cmd, _ in calls)
    assert any("test:perf:ci" in " ".join(cmd) for cmd, _ in calls)
