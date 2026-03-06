from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.db.session import GuardedAsyncSession


@pytest.mark.asyncio
async def test_guarded_async_session_rolls_back_on_commit_failure() -> None:
    session = object.__new__(GuardedAsyncSession)
    commit_error = SQLAlchemyError("commit failed")

    with (
        patch.object(AsyncSession, "commit", AsyncMock(side_effect=commit_error)),
        patch.object(AsyncSession, "rollback", AsyncMock()) as rollback_mock,
    ):
        with pytest.raises(SQLAlchemyError):
            await GuardedAsyncSession.commit(session)

    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_guarded_async_session_logs_when_rollback_fails() -> None:
    session = object.__new__(GuardedAsyncSession)
    commit_error = SQLAlchemyError("commit failed")
    rollback_error = SQLAlchemyError("rollback failed")

    with (
        patch.object(AsyncSession, "commit", AsyncMock(side_effect=commit_error)),
        patch.object(AsyncSession, "rollback", AsyncMock(side_effect=rollback_error)),
        patch("app.shared.db.session.logger") as mock_logger,
    ):
        with pytest.raises(SQLAlchemyError):
            await GuardedAsyncSession.commit(session)

    mock_logger.error.assert_called_once()

