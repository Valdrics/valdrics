from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

from scripts.verify_dashboard_runtime_contract import (
    main,
    verify_dashboard_runtime_contract,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_dashboard_runtime_layout(root: Path) -> None:
    _write(
        root / "Dockerfile.dashboard",
        'COPY --from=builder /app/.svelte-kit/output ./build\nCMD ["node", "server.node.mjs"]\n',
    )
    _write(
        root / "dashboard" / "server.node.mjs",
        "import { Server } from './build/server/index.js';\n"
        "import { manifest } from './build/server/manifest.js';\n"
        "await app.init({ env: process.env });\n",
    )
    _write(root / "dashboard" / ".svelte-kit" / "output" / "server" / "index.js", "export {};\n")
    _write(
        root / "dashboard" / ".svelte-kit" / "output" / "server" / "manifest.js",
        "export const manifest = {};\n",
    )
    _write(
        root / "dashboard" / ".svelte-kit" / "output" / "client" / "_app" / "version.json",
        '{"version":"test"}\n',
    )


def test_verify_dashboard_runtime_contract_accepts_matching_layout(tmp_path: Path) -> None:
    _seed_dashboard_runtime_layout(tmp_path)

    errors = verify_dashboard_runtime_contract(
        root=tmp_path,
        smoke_runner=lambda _root: None,
    )

    assert errors == []


def test_verify_dashboard_runtime_contract_reports_missing_artifacts(tmp_path: Path) -> None:
    errors = verify_dashboard_runtime_contract(root=tmp_path, skip_smoke=True)
    assert any("missing required dashboard runtime artifact" in error for error in errors)


def test_verify_dashboard_runtime_contract_reports_smoke_failure(tmp_path: Path) -> None:
    _seed_dashboard_runtime_layout(tmp_path)

    errors = verify_dashboard_runtime_contract(
        root=tmp_path,
        smoke_runner=lambda _root: "dashboard runtime smoke failed: refused connection",
    )

    assert errors == ["dashboard runtime smoke failed: refused connection"]


@pytest.mark.skipif(fcntl is None, reason="requires POSIX file locking")
def test_verify_dashboard_runtime_contract_reports_lock_timeout(tmp_path: Path) -> None:
    _seed_dashboard_runtime_layout(tmp_path)
    lock_path = tmp_path / ".runtime" / "locks" / "dashboard-runtime-contract.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with contextlib.ExitStack():
            errors = verify_dashboard_runtime_contract(
                root=tmp_path,
                skip_smoke=True,
                lock_timeout_seconds=0.01,
            )

    assert len(errors) == 1
    assert "dashboard runtime contract lock could not be acquired" in errors[0]


def test_main_reports_success_and_failure(tmp_path: Path, capsys) -> None:
    _seed_dashboard_runtime_layout(tmp_path)

    assert main(["--root", str(tmp_path), "--skip-smoke"]) == 0
    assert "[dashboard-runtime] ok" in capsys.readouterr().out

    broken_root = tmp_path / "broken"
    broken_root.mkdir()
    assert main(["--root", str(broken_root), "--skip-smoke"]) == 1
    assert "[dashboard-runtime] FAILED" in capsys.readouterr().out
