"""Verify supply-chain artifact attestations with GitHub CLI."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess  # nosec B404 - controlled GitHub CLI invocation only
import time
from collections.abc import Sequence
from pathlib import Path

MIN_GH_VERSION: tuple[int, int, int] = (2, 67, 0)
DEFAULT_SIGNER_WORKFLOW = ".github/workflows/sbom.yml"
DEFAULT_VERIFY_MAX_ATTEMPTS = 4
DEFAULT_VERIFY_INITIAL_RETRY_DELAY_SECONDS = 2.0
DEFAULT_ARTIFACT_PATHS: tuple[Path, ...] = (
    Path("sbom/valdrics-python-sbom.json"),
    Path("sbom/valdrics-container-sbom.json"),
    Path("provenance/supply-chain-manifest.json"),
)
REPO_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GITHUB_REMOTE_PATTERN = re.compile(
    r"(?:git@github\.com:|https://github\.com/|ssh://git@github\.com/)"
    r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def _format_command(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def _resolve_gh_executable() -> str:
    gh_executable = shutil.which("gh")
    if not gh_executable:
        raise RuntimeError("GitHub CLI executable `gh` is required")
    return gh_executable


def _resolve_git_executable() -> str:
    git_executable = shutil.which("git")
    if not git_executable:
        raise RuntimeError("Git executable `git` is required")
    return git_executable


def _normalize_repo_slug(value: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    if REPO_SLUG_PATTERN.fullmatch(candidate) is None:
        raise ValueError("`repo` is required (OWNER/REPO).")
    return candidate


def _repo_slug_from_remote_url(remote_url: str) -> str:
    match = GITHUB_REMOTE_PATTERN.fullmatch(str(remote_url or "").strip())
    if match is None:
        return ""
    return f"{match.group('owner')}/{match.group('repo')}"


def _resolve_repo_from_git_remote() -> str:
    try:
        git_executable = _resolve_git_executable()
    except RuntimeError:
        return ""
    completed = subprocess.run(
        [git_executable, "remote", "get-url", "origin"],
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603 - fixed git subcommand with no shell expansion
    if completed.returncode != 0:
        return ""
    return _repo_slug_from_remote_url(completed.stdout)


def _resolve_repo_slug(value: str) -> str:
    explicit = _normalize_repo_slug(value)
    if explicit:
        return explicit
    env_repo = _normalize_repo_slug(os.environ.get("GITHUB_REPOSITORY", ""))
    if env_repo:
        return env_repo
    remote_repo = _normalize_repo_slug(_resolve_repo_from_git_remote())
    if remote_repo:
        return remote_repo
    raise ValueError("`repo` is required (OWNER/REPO).")


def _resolve_artifact_paths(artifacts: Sequence[Path]) -> tuple[Path, ...]:
    if artifacts:
        return tuple(artifacts)
    return DEFAULT_ARTIFACT_PATHS


def _run_gh_command(
    args: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    gh_executable = _resolve_gh_executable()
    return subprocess.run(
        [gh_executable, *args],
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603 - trusted gh CLI invocation with fixed argument structure


def _materialize_gh_command(cmd: Sequence[str]) -> list[str]:
    if not cmd or cmd[0] != "gh":
        raise ValueError(f"Unexpected gh command shape: {cmd!r}")
    return [_resolve_gh_executable(), *list(cmd[1:])]


def _parse_semver(version_text: str) -> tuple[int, int, int]:
    match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version_text)
    if match is None:
        raise ValueError(f"Unable to parse semantic version from: {version_text!r}")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def check_gh_cli_version() -> tuple[int, int, int]:
    completed = _run_gh_command(("version",))
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"Failed to execute `gh version` for attestation verification: {message}"
        )

    version = _parse_semver(completed.stdout)
    if version < MIN_GH_VERSION:
        raise RuntimeError(
            "GitHub CLI version is too old for safe attestation verification: "
            f"found {version[0]}.{version[1]}.{version[2]}, "
            f"required >= {MIN_GH_VERSION[0]}.{MIN_GH_VERSION[1]}.{MIN_GH_VERSION[2]}"
        )

    attestation_help = _run_gh_command(("attestation", "verify", "--help"))
    if attestation_help.returncode != 0:
        details = attestation_help.stderr.strip() or attestation_help.stdout.strip()
        raise RuntimeError(
            "Installed GitHub CLI does not support `gh attestation verify`: "
            f"{details}"
        )
    return version


def build_verify_command(
    *,
    artifact: Path,
    repo: str,
    signer_workflow: str,
) -> list[str]:
    return [
        "gh",
        "attestation",
        "verify",
        str(artifact),
        "--repo",
        repo,
        "--signer-workflow",
        signer_workflow,
        "--format",
        "json",
    ]


def _assert_verification_output(stdout: str, *, artifact: Path) -> None:
    raw = stdout.strip()
    if not raw:
        raise RuntimeError(
            f"Attestation verification produced empty output for {artifact.as_posix()}"
        )

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Attestation verification did not return JSON for {artifact.as_posix()}"
        ) from exc

    if isinstance(payload, list):
        if len(payload) == 0:
            raise RuntimeError(
                f"Attestation verification returned no entries for {artifact.as_posix()}"
            )
        return

    if isinstance(payload, dict) and payload:
        return

    raise RuntimeError(
        "Attestation verification returned unsupported JSON payload type "
        f"for {artifact.as_posix()}: {type(payload).__name__}"
    )


def _is_transient_verification_failure(details: str) -> bool:
    candidate = str(details or "").strip().lower()
    if not candidate:
        return False
    transient_markers = (
        'verifying with issuer "sigstore.dev"',
        "no attestations found",
        "not yet available",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "try again",
    )
    return any(marker in candidate for marker in transient_markers)


def verify_attestations(
    *,
    repo: str,
    signer_workflow: str,
    artifacts: Sequence[Path],
    dry_run: bool,
) -> int:
    if not repo.strip():
        raise ValueError("`repo` is required (OWNER/REPO).")
    if not signer_workflow.strip():
        raise ValueError("`signer_workflow` must be non-empty.")
    if not artifacts:
        raise ValueError("At least one --artifact is required.")

    if not dry_run:
        for artifact in artifacts:
            artifact_path = artifact.resolve()
            if not artifact_path.exists() or not artifact_path.is_file():
                raise FileNotFoundError(
                    f"Artifact path does not exist or is not a file: {artifact.as_posix()}"
                )

    if not dry_run:
        gh_version = check_gh_cli_version()
        print(
            "[attestation-verify] using gh "
            f"{gh_version[0]}.{gh_version[1]}.{gh_version[2]}"
        )

    for artifact in artifacts:
        artifact_path = artifact.resolve()
        cmd = build_verify_command(
            artifact=artifact_path,
            repo=repo,
            signer_workflow=signer_workflow,
        )
        if dry_run and (not artifact_path.exists() or not artifact_path.is_file()):
            print(
                "[attestation-verify] warning missing local artifact in dry-run: "
                f"{artifact.as_posix()}"
            )
        print(f"[attestation-verify] {_format_command(cmd)}")
        if dry_run:
            continue

        retry_delay_seconds = DEFAULT_VERIFY_INITIAL_RETRY_DELAY_SECONDS
        for attempt in range(1, DEFAULT_VERIFY_MAX_ATTEMPTS + 1):
            completed = subprocess.run(
                _materialize_gh_command(cmd),
                check=False,
                capture_output=True,
                text=True,
            )  # nosec B603 - trusted gh CLI invocation with validated local artifact path
            if completed.returncode == 0:
                _assert_verification_output(completed.stdout, artifact=artifact_path)
                break

            details = completed.stderr.strip() or completed.stdout.strip()
            is_retryable = _is_transient_verification_failure(details)
            if not is_retryable or attempt == DEFAULT_VERIFY_MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Attestation verification failed for {artifact.as_posix()}: {details}"
                )

            print(
                "[attestation-verify] transient verification failure for "
                f"{artifact.as_posix()} on attempt {attempt}/"
                f"{DEFAULT_VERIFY_MAX_ATTEMPTS}; retrying in "
                f"{retry_delay_seconds:.1f}s"
            )
            time.sleep(retry_delay_seconds)
            retry_delay_seconds *= 2
    return 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify GitHub artifact attestations for supply-chain evidence files."
        )
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help=(
            "Repository in OWNER/REPO format "
            "(defaults to $GITHUB_REPOSITORY, then git origin remote)."
        ),
    )
    parser.add_argument(
        "--signer-workflow",
        default=DEFAULT_SIGNER_WORKFLOW,
        help=(
            "Expected signer workflow path used by GitHub attestation verification "
            "(default: .github/workflows/sbom.yml)."
        ),
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "Artifact file path to verify; may be supplied multiple times. "
            "Defaults to the workflow subject paths when omitted."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print verification commands without executing them.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    artifacts = _resolve_artifact_paths(tuple(Path(item) for item in args.artifact))
    return verify_attestations(
        repo=_resolve_repo_slug(str(args.repo)),
        signer_workflow=str(args.signer_workflow),
        artifacts=artifacts,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
