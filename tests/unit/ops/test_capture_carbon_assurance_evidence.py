from __future__ import annotations

import pytest

import scripts.capture_carbon_assurance_evidence as carbon_script


def test_require_valid_base_url_accepts_localhost_without_scheme() -> None:
    assert (
        carbon_script._require_valid_base_url("127.0.0.1:8000")
        == "http://127.0.0.1:8000"
    )


def test_main_surfaces_connection_failure_cleanly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def post(self, url, json):
            request = carbon_script.httpx.Request("POST", url)
            raise carbon_script.httpx.ConnectError("boom", request=request)

    monkeypatch.setattr(carbon_script.httpx, "Client", Client)

    with pytest.raises(SystemExit, match="Capture failed while calling"):
        carbon_script.main(
            [
                "--url",
                "http://127.0.0.1:8000",
                "--token",
                "abc.def.ghi",
            ]
        )
