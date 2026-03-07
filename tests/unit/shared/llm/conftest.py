from __future__ import annotations

import pytest

from tests.unit.shared.llm.budget_fair_use_test_helpers import DummyManager


@pytest.fixture(autouse=True)
def _reset_fair_use_local_counts() -> None:
    DummyManager._local_inflight_counts.clear()
    DummyManager._local_global_abuse_block_until = None
