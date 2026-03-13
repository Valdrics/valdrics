from __future__ import annotations

from scripts.cla_assistant import (
    COMMENT_MARKER,
    ClaState,
    GitHubApiError,
    SignatureEntry,
    _build_comment_body,
    _comment_and_status_for_pr,
    _collect_required_signers,
    _evaluate_cla_state,
    _normalize_signatures,
    _serialize_signatures,
    _upsert_signature,
)


def test_collect_required_signers_includes_pr_author_and_commit_authors() -> None:
    signers = _collect_required_signers(
        pr_author="alice",
        commit_authors=("alice", "bob", "dependabot[bot]"),
        allowlist=("dependabot[bot]", "github-actions[bot]"),
    )

    assert signers == ("alice", "bob")


def test_upsert_signature_replaces_existing_entry_without_duplication() -> None:
    signatures = (
        SignatureEntry(
            name="alice",
            id=1,
            comment_id=100,
            created_at="2026-03-01T00:00:00Z",
            repo_id=10,
            pull_request_no=12,
        ),
    )

    updated = _upsert_signature(
        signatures,
        login="alice",
        user_id=1,
        comment_id=200,
        created_at="2026-03-02T00:00:00Z",
        repo_id=10,
        pull_request_no=99,
    )

    assert len(updated) == 1
    assert updated[0].comment_id == 200
    assert updated[0].pull_request_no == 99
    assert updated[0].created_at == "2026-03-02T00:00:00Z"


def test_normalize_and_serialize_signatures_round_trip() -> None:
    payload = {
        "signedContributors": [
            {
                "name": "alice",
                "id": 1,
                "comment_id": 100,
                "created_at": "2026-03-01T00:00:00Z",
                "repoId": 10,
                "pullRequestNo": 12,
            }
        ]
    }

    normalized = _normalize_signatures(payload)
    rendered = _serialize_signatures(normalized)

    assert '"name": "alice"' in rendered
    assert '"repoId": 10' in rendered
    assert normalized[0].name == "alice"


def test_evaluate_cla_state_marks_missing_signers() -> None:
    state = _evaluate_cla_state(
        required_signers=("alice", "bob"),
        signatures=(
            SignatureEntry(
                name="alice",
                id=1,
                comment_id=100,
                created_at="2026-03-01T00:00:00Z",
                repo_id=10,
                pull_request_no=12,
            ),
        ),
    )

    assert isinstance(state, ClaState)
    assert state.is_satisfied is False
    assert state.signed_required_signers == ("alice",)
    assert state.missing_signers == ("bob",)


def test_build_comment_body_for_unsigned_pr_contains_exact_phrase() -> None:
    body = _build_comment_body(
        state=ClaState(
            required_signers=("alice", "bob"),
            signed_required_signers=("alice",),
            missing_signers=("bob",),
        ),
        sign_phrase="I have read the CLA Document and I hereby sign the CLA",
        document_url="https://github.com/Valdrics/valdrics/blob/main/CLA.md",
    )

    assert COMMENT_MARKER in body
    assert "Missing signatures: @bob" in body
    assert "I have read the CLA Document and I hereby sign the CLA" in body


def test_build_comment_body_for_signed_pr_reports_success() -> None:
    body = _build_comment_body(
        state=ClaState(
            required_signers=("alice", "bob"),
            signed_required_signers=("alice", "bob"),
            missing_signers=(),
        ),
        sign_phrase="ignored",
        document_url="https://github.com/Valdrics/valdrics/blob/main/CLA.md",
    )

    assert COMMENT_MARKER in body
    assert "CLA requirements satisfied" in body
    assert "@alice, @bob" in body


def test_comment_sync_403_does_not_block_status_update() -> None:
    recorded_statuses: list[dict[str, str]] = []

    class _Client:
        def list_issue_comments(self, _number: int):
            return []

        def create_issue_comment(self, _number: int, _body: str):
            raise GitHubApiError(
                "GitHub API POST /repos/Valdrics/valdrics/issues/295/comments failed: 403"
            )

        def update_issue_comment(self, _comment_id: int, _body: str):
            raise AssertionError("update should not be called")

        def create_commit_status(
            self,
            *,
            sha: str,
            state: str,
            description: str,
            target_url: str,
            context: str,
        ) -> None:
            recorded_statuses.append(
                {
                    "sha": sha,
                    "state": state,
                    "description": description,
                    "target_url": target_url,
                    "context": context,
                }
            )

    _comment_and_status_for_pr(
        client=_Client(),  # type: ignore[arg-type]
        pr={
            "number": 295,
            "html_url": "https://github.com/Valdrics/valdrics/pull/295",
            "head": {"sha": "abc123"},
        },
        state=ClaState(
            required_signers=("alice",),
            signed_required_signers=(),
            missing_signers=("alice",),
        ),
        sign_phrase="I have read the CLA Document and I hereby sign the CLA",
        document_url="https://github.com/Valdrics/valdrics/blob/main/CLA.md",
        status_context="cla-assistant",
    )

    assert recorded_statuses == [
        {
            "sha": "abc123",
            "state": "failure",
            "description": "CLA signature required",
            "target_url": "https://github.com/Valdrics/valdrics/pull/295",
            "context": "cla-assistant",
        }
    ]
