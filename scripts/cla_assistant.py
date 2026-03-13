#!/usr/bin/env python3
"""Permanent in-repo CLA workflow helper.

This script replaces the unmaintained third-party contributor-assistant action.
It preserves the existing repository behavior:
- signatures are stored on the dedicated `cla-signatures` branch
- contributors sign by commenting an exact phrase on the PR
- pull requests receive a passing/failing commit status based on signature state
- the PR gets a stable bot comment with next steps or success state
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_SIGN_PHRASE = "I have read the CLA Document and I hereby sign the CLA"
DEFAULT_SIGNATURES_PATH = "signatures/version1/cla.json"
DEFAULT_SIGNATURE_BRANCH = "cla-signatures"
DEFAULT_STATUS_CONTEXT = "cla-assistant"
COMMENT_MARKER = "<!-- valdrics-cla-assistant -->"
DEFAULT_ALLOWLIST = (
    "dependabot[bot]",
    "renovate[bot]",
    "github-actions[bot]",
)


@dataclass(frozen=True)
class SignatureEntry:
    name: str
    id: int | None
    comment_id: int | None
    created_at: str
    repo_id: int | None
    pull_request_no: int | None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "created_at": self.created_at,
        }
        if self.id is not None:
            payload["id"] = self.id
        if self.comment_id is not None:
            payload["comment_id"] = self.comment_id
        if self.repo_id is not None:
            payload["repoId"] = self.repo_id
        if self.pull_request_no is not None:
            payload["pullRequestNo"] = self.pull_request_no
        return payload


@dataclass(frozen=True)
class ClaState:
    required_signers: tuple[str, ...]
    signed_required_signers: tuple[str, ...]
    missing_signers: tuple[str, ...]

    @property
    def is_satisfied(self) -> bool:
        return len(self.missing_signers) == 0


class GitHubApiError(RuntimeError):
    pass


class GitHubClient:
    def __init__(
        self,
        *,
        token: str,
        repository: str,
        api_url: str,
    ) -> None:
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        if not repository:
            raise ValueError("GITHUB_REPOSITORY is required")
        self._token = token
        self._repository = repository
        self._api_url = api_url.rstrip("/")

    def get_json(self, path: str) -> Any:
        return self._request_json("GET", path)

    def post_json(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request_json("POST", path, payload)

    def put_json(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request_json("PUT", path, payload)

    def patch_json(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request_json("PATCH", path, payload)

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._api_url}{path}"
        data = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "valdrics-cla-assistant",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise GitHubApiError(
                f"GitHub API {method} {path} failed: {exc.code} {body}"
            ) from exc
        return json.loads(raw) if raw else None

    def get_pull_request(self, number: int) -> dict[str, Any]:
        return self.get_json(f"/repos/{self._repository}/pulls/{number}")

    def list_pull_request_commits(self, number: int) -> list[dict[str, Any]]:
        commits: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self.get_json(
                f"/repos/{self._repository}/pulls/{number}/commits?per_page=100&page={page}"
            )
            if not isinstance(batch, list) or not batch:
                break
            commits.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return commits

    def list_issue_comments(self, number: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self.get_json(
                f"/repos/{self._repository}/issues/{number}/comments?per_page=100&page={page}"
            )
            if not isinstance(batch, list) or not batch:
                break
            comments.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return comments

    def create_issue_comment(self, number: int, body: str) -> dict[str, Any]:
        return self.post_json(
            f"/repos/{self._repository}/issues/{number}/comments",
            {"body": body},
        )

    def update_issue_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        return self.patch_json(
            f"/repos/{self._repository}/issues/comments/{comment_id}",
            {"body": body},
        )

    def create_commit_status(
        self,
        *,
        sha: str,
        state: str,
        description: str,
        target_url: str,
        context: str,
    ) -> None:
        self.post_json(
            f"/repos/{self._repository}/statuses/{sha}",
            {
                "state": state,
                "description": description[:140],
                "target_url": target_url,
                "context": context,
            },
        )

    def get_ref(self, branch: str) -> dict[str, Any]:
        return self.get_json(
            f"/repos/{self._repository}/git/ref/heads/{quote(branch, safe='')}"
        )

    def create_ref(self, branch: str, sha: str) -> None:
        self.post_json(
            f"/repos/{self._repository}/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": sha},
        )

    def get_file(self, path: str, *, ref: str) -> dict[str, Any] | None:
        try:
            payload = self.get_json(
                f"/repos/{self._repository}/contents/{quote(path, safe='/')}?ref={quote(ref, safe='')}"
            )
        except GitHubApiError as exc:
            if " 404 " in str(exc):
                return None
            raise
        if not isinstance(payload, dict):
            raise GitHubApiError(f"Unexpected file payload for {path} on {ref}")
        return payload

    def put_file(
        self,
        *,
        path: str,
        branch: str,
        message: str,
        content: str,
        sha: str | None,
    ) -> None:
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        self.put_json(
            f"/repos/{self._repository}/contents/{quote(path, safe='/')}",
            payload,
        )


def _normalize_allowlist(raw: str) -> tuple[str, ...]:
    tokens = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(sorted(set(tokens)))


def _normalize_signatures(payload: dict[str, Any] | None) -> tuple[SignatureEntry, ...]:
    if not isinstance(payload, dict):
        return tuple()
    contributors = payload.get("signedContributors")
    if not isinstance(contributors, list):
        return tuple()
    normalized: list[SignatureEntry] = []
    for item in contributors:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        created_at = str(item.get("created_at") or "").strip()
        if not name or not created_at:
            continue
        normalized.append(
            SignatureEntry(
                name=name,
                id=item.get("id") if isinstance(item.get("id"), int) else None,
                comment_id=(
                    item.get("comment_id")
                    if isinstance(item.get("comment_id"), int)
                    else None
                ),
                created_at=created_at,
                repo_id=(
                    item.get("repoId") if isinstance(item.get("repoId"), int) else None
                ),
                pull_request_no=(
                    item.get("pullRequestNo")
                    if isinstance(item.get("pullRequestNo"), int)
                    else None
                ),
            )
        )
    return tuple(sorted(normalized, key=lambda item: item.name.casefold()))


def _serialize_signatures(signatures: tuple[SignatureEntry, ...]) -> str:
    payload = {
        "signedContributors": [entry.to_payload() for entry in signatures],
    }
    return json.dumps(payload, indent=2) + "\n"


def _upsert_signature(
    signatures: tuple[SignatureEntry, ...],
    *,
    login: str,
    user_id: int | None,
    comment_id: int | None,
    repo_id: int | None,
    pull_request_no: int | None,
    created_at: str,
) -> tuple[SignatureEntry, ...]:
    updated: list[SignatureEntry] = [
        entry for entry in signatures if entry.name.casefold() != login.casefold()
    ]
    updated.append(
        SignatureEntry(
            name=login,
            id=user_id,
            comment_id=comment_id,
            created_at=created_at,
            repo_id=repo_id,
            pull_request_no=pull_request_no,
        )
    )
    return tuple(sorted(updated, key=lambda item: item.name.casefold()))


def _collect_required_signers(
    *,
    pr_author: str,
    commit_authors: tuple[str, ...],
    allowlist: tuple[str, ...],
) -> tuple[str, ...]:
    allow = {item.casefold() for item in allowlist}
    unique = {pr_author.strip()}
    unique.update(author.strip() for author in commit_authors if author.strip())
    return tuple(
        sorted(
            login for login in unique if login and login.casefold() not in allow
        )
    )


def _evaluate_cla_state(
    *,
    required_signers: tuple[str, ...],
    signatures: tuple[SignatureEntry, ...],
) -> ClaState:
    signed_names = {entry.name.casefold(): entry.name for entry in signatures}
    signed_required = tuple(
        signer for signer in required_signers if signer.casefold() in signed_names
    )
    missing = tuple(
        signer for signer in required_signers if signer.casefold() not in signed_names
    )
    return ClaState(
        required_signers=required_signers,
        signed_required_signers=signed_required,
        missing_signers=missing,
    )


def _cla_document_url(*, server_url: str, repository: str, default_branch: str) -> str:
    return f"{server_url.rstrip('/')}/{repository}/blob/{default_branch}/CLA.md"


def _build_comment_body(
    *,
    state: ClaState,
    sign_phrase: str,
    document_url: str,
) -> str:
    if state.is_satisfied:
        if state.required_signers:
            signer_line = ", ".join(f"@{signer}" for signer in state.required_signers)
        else:
            signer_line = "No external signers required for this pull request."
        return (
            f"{COMMENT_MARKER}\n"
            "CLA requirements satisfied.\n\n"
            f"Signed contributors: {signer_line}"
        )

    missing = ", ".join(f"@{signer}" for signer in state.missing_signers)
    return (
        f"{COMMENT_MARKER}\n"
        "Thank you for the contribution. Please review "
        f"[`CLA.md`]({document_url}) and sign by commenting exactly:\n"
        f"`{sign_phrase}`\n\n"
        f"Missing signatures: {missing}"
    )


def _find_existing_comment_id(comments: list[dict[str, Any]]) -> int | None:
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = str(comment.get("body") or "")
        if COMMENT_MARKER not in body:
            continue
        comment_id = comment.get("id")
        if isinstance(comment_id, int):
            return comment_id
    return None


def _extract_commit_authors(commits: list[dict[str, Any]]) -> tuple[str, ...]:
    authors: set[str] = set()
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        author = commit.get("author")
        if isinstance(author, dict):
            login = str(author.get("login") or "").strip()
            if login:
                authors.add(login)
    return tuple(sorted(authors))


def _load_event(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("GitHub event payload must be a JSON object")
    return payload


def _get_pull_request_number(event_name: str, event: dict[str, Any]) -> int:
    if event_name == "pull_request_target":
        number = event.get("number")
        if isinstance(number, int):
            return number
    issue = event.get("issue")
    if isinstance(issue, dict):
        number = issue.get("number")
        if isinstance(number, int):
            return number
    raise ValueError("Unable to resolve pull request number from event payload")


def _ensure_signature_branch(
    *,
    client: GitHubClient,
    branch: str,
    default_branch: str,
) -> None:
    try:
        client.get_ref(branch)
        return
    except GitHubApiError as exc:
        if " 404 " not in str(exc):
            raise
    default_ref = client.get_ref(default_branch)
    default_sha = (
        default_ref.get("object", {}).get("sha") if isinstance(default_ref, dict) else None
    )
    if not isinstance(default_sha, str) or not default_sha:
        raise GitHubApiError(
            f"Unable to resolve default branch SHA for {default_branch}"
        )
    client.create_ref(branch, default_sha)


def _load_signatures(
    *,
    client: GitHubClient,
    branch: str,
    path: str,
) -> tuple[tuple[SignatureEntry, ...], str | None]:
    payload = client.get_file(path, ref=branch)
    if payload is None:
        return tuple(), None
    raw_content = str(payload.get("content") or "")
    encoding = str(payload.get("encoding") or "")
    if encoding != "base64":
        raise GitHubApiError(f"Unexpected encoding for {path} on {branch}: {encoding}")
    decoded = base64.b64decode(raw_content).decode("utf-8")
    content_payload = json.loads(decoded)
    sha = payload.get("sha") if isinstance(payload.get("sha"), str) else None
    return _normalize_signatures(content_payload), sha


def _comment_and_status_for_pr(
    *,
    client: GitHubClient,
    pr: dict[str, Any],
    state: ClaState,
    sign_phrase: str,
    document_url: str,
    status_context: str,
) -> None:
    number = int(pr["number"])
    html_url = str(pr.get("html_url") or "")
    head_sha = str(pr.get("head", {}).get("sha") or "")
    if not head_sha:
        raise GitHubApiError("Pull request head SHA is missing")

    body = _build_comment_body(
        state=state,
        sign_phrase=sign_phrase,
        document_url=document_url,
    )
    comments = client.list_issue_comments(number)
    existing_comment_id = _find_existing_comment_id(comments)
    if existing_comment_id is None:
        client.create_issue_comment(number, body)
    else:
        client.update_issue_comment(existing_comment_id, body)

    if state.is_satisfied:
        description = "CLA requirements satisfied"
        status_state = "success"
    else:
        count = len(state.missing_signers)
        description = (
            "CLA signature required"
            if count == 1
            else f"CLA signatures required from {count} contributors"
        )
        status_state = "failure"

    client.create_commit_status(
        sha=head_sha,
        state=status_state,
        description=description,
        target_url=html_url,
        context=status_context,
    )


def run(
    *,
    event_name: str,
    event: dict[str, Any],
    client: GitHubClient,
    signatures_path: str,
    signatures_branch: str,
    sign_phrase: str,
    allowlist: tuple[str, ...],
    repository: str,
    server_url: str,
    status_context: str,
) -> int:
    action = str(event.get("action") or "")
    if event_name == "pull_request_target" and action == "closed":
        return 0

    pr_number = _get_pull_request_number(event_name, event)
    pr = client.get_pull_request(pr_number)
    default_branch = str(event.get("repository", {}).get("default_branch") or "main")

    _ensure_signature_branch(
        client=client,
        branch=signatures_branch,
        default_branch=default_branch,
    )
    signatures, signatures_sha = _load_signatures(
        client=client,
        branch=signatures_branch,
        path=signatures_path,
    )

    if event_name == "issue_comment":
        comment = event.get("comment")
        if isinstance(comment, dict):
            body = str(comment.get("body") or "").strip()
            commenter = comment.get("user") if isinstance(comment.get("user"), dict) else {}
            commenter_login = str(commenter.get("login") or "").strip()
            commenter_id = commenter.get("id") if isinstance(commenter.get("id"), int) else None
            comment_id = comment.get("id") if isinstance(comment.get("id"), int) else None
            if body == sign_phrase and commenter_login:
                created_at = str(comment.get("created_at") or datetime.now(timezone.utc).isoformat())
                repo_id = event.get("repository", {}).get("id")
                signatures = _upsert_signature(
                    signatures,
                    login=commenter_login,
                    user_id=commenter_id,
                    comment_id=comment_id,
                    repo_id=repo_id if isinstance(repo_id, int) else None,
                    pull_request_no=pr_number,
                    created_at=created_at,
                )
                client.put_file(
                    path=signatures_path,
                    branch=signatures_branch,
                    message=f"cla: sign {commenter_login}",
                    content=_serialize_signatures(signatures),
                    sha=signatures_sha,
                )

    commit_authors = _extract_commit_authors(client.list_pull_request_commits(pr_number))
    required_signers = _collect_required_signers(
        pr_author=str(pr.get("user", {}).get("login") or "").strip(),
        commit_authors=commit_authors,
        allowlist=allowlist,
    )
    state = _evaluate_cla_state(required_signers=required_signers, signatures=signatures)
    document_url = _cla_document_url(
        server_url=server_url,
        repository=repository,
        default_branch=default_branch,
    )
    _comment_and_status_for_pr(
        client=client,
        pr=pr,
        state=state,
        sign_phrase=sign_phrase,
        document_url=document_url,
        status_context=status_context,
    )

    if event_name == "pull_request_target" and not state.is_satisfied:
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the in-repo CLA assistant")
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument(
        "--event-path",
        default=os.environ.get("GITHUB_EVENT_PATH", ""),
        help="Path to the GitHub Actions event payload JSON.",
    )
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--server-url", default=os.environ.get("GITHUB_SERVER_URL", "https://github.com"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--signatures-path", default=DEFAULT_SIGNATURES_PATH)
    parser.add_argument("--signatures-branch", default=DEFAULT_SIGNATURE_BRANCH)
    parser.add_argument("--sign-phrase", default=DEFAULT_SIGN_PHRASE)
    parser.add_argument(
        "--allowlist",
        default=",".join(DEFAULT_ALLOWLIST),
        help="Comma-separated GitHub logins that do not need a CLA signature.",
    )
    parser.add_argument("--status-context", default=DEFAULT_STATUS_CONTEXT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.event_name:
        raise SystemExit("GITHUB_EVENT_NAME/--event-name is required")
    if not args.event_path:
        raise SystemExit("GITHUB_EVENT_PATH/--event-path is required")
    event = _load_event(Path(args.event_path))
    client = GitHubClient(
        token=str(args.token),
        repository=str(args.repository),
        api_url=str(args.api_url),
    )
    return run(
        event_name=str(args.event_name),
        event=event,
        client=client,
        signatures_path=str(args.signatures_path),
        signatures_branch=str(args.signatures_branch),
        sign_phrase=str(args.sign_phrase),
        allowlist=_normalize_allowlist(str(args.allowlist)),
        repository=str(args.repository),
        server_url=str(args.server_url),
        status_context=str(args.status_context),
    )


if __name__ == "__main__":
    raise SystemExit(main())
