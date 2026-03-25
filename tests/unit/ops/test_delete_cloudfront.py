from __future__ import annotations

import pytest

from scripts import delete_cloudfront


def test_delete_cloudfront_times_out_when_distribution_never_stabilizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Client:
        def get_distribution_config(self, *, Id: str):
            del Id
            return {
                "ETag": "etag-1",
                "DistributionConfig": {"Enabled": False},
            }

        def get_distribution(self, *, Id: str):
            del Id
            return {"Distribution": {"Status": "InProgress"}}

    monotonic_values = iter((0.0, 5.0, 11.0))
    sleeps: list[int] = []

    monkeypatch.setattr(delete_cloudfront.boto3, "client", lambda service: Client())

    with pytest.raises(RuntimeError, match="Timed out waiting to delete distribution"):
        delete_cloudfront.delete_cloudfront(
            distribution_id="dist-123",
            dry_run=False,
            max_wait_seconds=10,
            monotonic_fn=lambda: next(monotonic_values),
            sleep_fn=lambda seconds: sleeps.append(seconds),
        )

    assert sleeps == [15]
