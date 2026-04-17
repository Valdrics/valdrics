#!/usr/bin/env python3
"""Verify the dashboard container runtime contract used by managed deployments."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Callable
from urllib.error import URLError
from urllib.request import urlopen

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import repo_root_for, resolve_cli_path_from_root


DEFAULT_ROOT = repo_root_for(__file__)
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_LOCK_TIMEOUT_SECONDS = 300.0

BuildRunner = Callable[[Path], None]
SmokeRunner = Callable[[Path], str | None]


def _required_paths(root: Path) -> tuple[Path, ...]:
    dashboard_root = root / "dashboard"
    build_root = dashboard_root / ".svelte-kit" / "output"
    return (
        root / "Dockerfile.dashboard",
        dashboard_root / "server.node.mjs",
        build_root / "server" / "index.js",
        build_root / "server" / "manifest.js",
        build_root / "client" / "_app" / "version.json",
    )


def _text_contract_errors(root: Path) -> list[str]:
    errors: list[str] = []
    dockerfile_path = root / "Dockerfile.dashboard"
    server_path = root / "dashboard" / "server.node.mjs"

    dockerfile_text = dockerfile_path.read_text(encoding="utf-8")
    server_text = server_path.read_text(encoding="utf-8")

    if "COPY --from=builder /app/.svelte-kit/output ./build" not in dockerfile_text:
        errors.append(
            "Dockerfile.dashboard must copy .svelte-kit/output into ./build for the runtime image."
        )
    if 'CMD ["node", "server.node.mjs"]' not in dockerfile_text:
        errors.append("Dockerfile.dashboard must start the dashboard with node server.node.mjs.")
    if "await app.init({ env: process.env });" not in server_text:
        errors.append("dashboard/server.node.mjs must initialize the SvelteKit server with env.")
    if "import { Server } from './build/server/index.js';" not in server_text:
        errors.append("dashboard/server.node.mjs must import the built server entrypoint.")
    if "import { manifest } from './build/server/manifest.js';" not in server_text:
        errors.append("dashboard/server.node.mjs must import the built server manifest.")
    return errors


def build_dashboard(root: Path) -> None:
    subprocess.run(
        ["pnpm", "--dir", "dashboard", "run", "build"],
        cwd=root,
        check=True,
        text=True,
    )


def _dashboard_runtime_lock_path(root: Path) -> Path:
    return root / ".runtime" / "locks" / "dashboard-runtime-contract.lock"


@contextmanager
def _dashboard_runtime_lock(
    root: Path, *, timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS
):
    if fcntl is None:
        yield
        return

    lock_path = _dashboard_runtime_lock_path(root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "dashboard runtime contract lock could not be acquired within "
                        f"{timeout_seconds:.2f}s: {lock_path.as_posix()}"
                    )
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def smoke_dashboard_runtime(
    root: Path,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> str | None:
    dashboard_root = root / "dashboard"
    port = _reserve_local_port()
    origin = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "HOST": "127.0.0.1",
            "PORT": str(port),
            "ORIGIN": origin,
            "NODE_ENV": "production",
        }
    )

    process = subprocess.Popen(
        ["node", "server.node.mjs"],
        cwd=dashboard_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    response_preview = ""
    last_error = ""
    deadline = time.monotonic() + timeout_seconds

    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break

            try:
                with urlopen(f"{origin}/", timeout=2) as response:
                    body = response.read(4096).decode("utf-8", errors="replace")
                    response_preview = body[:200]
                    if response.status == 200 and "<html" in body.lower():
                        return None
                    last_error = (
                        f"unexpected dashboard response status={response.status} "
                        f"body_preview={response_preview!r}"
                    )
            except URLError as exc:
                last_error = str(exc.reason)
            except OSError as exc:
                last_error = str(exc)

            time.sleep(0.25)

        if not last_error:
            if process.poll() is not None:
                last_error = f"dashboard runtime exited early with code {process.returncode}"
            else:
                last_error = "dashboard runtime did not become ready before timeout"
        return _format_smoke_failure(process, last_error)
    finally:
        _stop_process(process)


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _format_smoke_failure(process: subprocess.Popen[str], message: str) -> str:
    logs = ""
    if process.stdout is not None:
        try:
            logs, _ = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            logs, _ = process.communicate(timeout=1)
    log_excerpt = logs.strip()
    if log_excerpt:
        return f"dashboard runtime smoke failed: {message}. logs={log_excerpt!r}"
    return f"dashboard runtime smoke failed: {message}"


def verify_dashboard_runtime_contract(
    *,
    root: Path = DEFAULT_ROOT,
    build: bool = False,
    skip_smoke: bool = False,
    lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    build_runner: BuildRunner = build_dashboard,
    smoke_runner: SmokeRunner | None = None,
) -> list[str]:
    repo_root = Path(root)
    if not repo_root.exists():
        return [f"root not found: {repo_root}"]
    if not repo_root.is_dir():
        return [f"root must be a directory: {repo_root}"]

    try:
        with _dashboard_runtime_lock(
            repo_root,
            timeout_seconds=lock_timeout_seconds,
        ):
            if build:
                build_runner(repo_root)

            errors: list[str] = []
            for path in _required_paths(repo_root):
                if not path.exists():
                    errors.append(
                        f"missing required dashboard runtime artifact: {path.as_posix()}"
                    )
                elif not path.is_file():
                    errors.append(
                        f"dashboard runtime artifact must be a file: {path.as_posix()}"
                    )

            if errors:
                return errors

            errors.extend(_text_contract_errors(repo_root))
            if errors:
                return errors

            if skip_smoke:
                return []

            runner = smoke_runner or (lambda root_path: smoke_dashboard_runtime(root_path))
            smoke_error = runner(repo_root)
            return [smoke_error] if smoke_error else []
    except TimeoutError as exc:
        return [str(exc)]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the dashboard managed-runtime contract by checking the built output, "
            "Node server wrapper, and optional localhost smoke path."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repository root to verify.",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Run `pnpm --dir dashboard run build` before verifying the runtime contract.",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip the localhost runtime smoke test and only verify files/text contracts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = resolve_cli_path_from_root(DEFAULT_ROOT, args.root, field_name="root")
    errors = verify_dashboard_runtime_contract(
        root=root,
        build=bool(args.build),
        skip_smoke=bool(args.skip_smoke),
    )
    if errors:
        print("[dashboard-runtime] FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[dashboard-runtime] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
