from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.modules.optimization.adapters.common.credentials import (
    resolve_azure_credentials,
    resolve_gcp_credentials,
)
from app.modules.optimization.adapters.common.rightsizing_common import (
    evaluate_max_samples,
    is_small_shape,
)
from app.modules.optimization.adapters.common.sync_bridge import (
    materialize_iterable,
    run_blocking,
)


@pytest.mark.asyncio
async def test_run_blocking_executes_function_in_async_context() -> None:
    mock_callable = MagicMock(return_value=5)
    result = await run_blocking(mock_callable, 2, 3)
    mock_callable.assert_called_once_with(2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_materialize_iterable_collects_generator_results() -> None:
    mock_iterable_builder = MagicMock(return_value=[0, 1, 2, 3])
    items = await materialize_iterable(mock_iterable_builder, 4)
    mock_iterable_builder.assert_called_once_with(4)
    assert items == [0, 1, 2, 3]


def test_evaluate_max_samples_tracks_threshold_and_max_value() -> None:
    evaluation = evaluate_max_samples([1.0, "x", 4.5, 11.0], threshold=10.0)
    assert evaluation.has_data is True
    assert evaluation.below_threshold is False
    assert evaluation.max_observed == 11.0


def test_is_small_shape_matches_token_case_insensitively() -> None:
    assert is_small_shape("E2-Micro", tokens=("micro",)) is True
    assert is_small_shape("m5.2xlarge", tokens=("micro", "small")) is False


def test_resolve_azure_credentials_requires_all_client_secret_fields() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        resolve_azure_credentials({"tenant_id": "tenant-only"})


def test_resolve_azure_credentials_accepts_credential_like_objects() -> None:
    credential_like = MagicMock()
    credential_like.get_token = MagicMock(return_value="token")
    assert resolve_azure_credentials(credential_like) is credential_like


def test_resolve_gcp_credentials_requires_service_account_fields() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        resolve_gcp_credentials({"client_email": "svc@example.com"})


def test_resolve_gcp_credentials_accepts_credential_like_objects() -> None:
    credential_like = MagicMock()
    credential_like.before_request = MagicMock()
    assert resolve_gcp_credentials(credential_like) is credential_like
