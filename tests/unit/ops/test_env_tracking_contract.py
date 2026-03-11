from __future__ import annotations

import subprocess


def _git_ls_files(*paths: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", *paths],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_local_env_file_is_not_tracked_but_template_is() -> None:
    tracked = _git_ls_files(".env", ".env.example")

    assert ".env" not in tracked
    assert ".env.example" in tracked
