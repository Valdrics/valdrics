from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import scripts.verify_alertmanager_channels as alertmanager_verifier
from scripts.verify_alertmanager_channels import (
    AlertmanagerVerificationError,
    main,
    verify_alertmanager_config,
)


def _load_repo_alertmanager_config() -> dict[str, object]:
    config_path = Path("prometheus/alertmanager.yml")
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def test_verify_alertmanager_config_accepts_repo_config() -> None:
    config = _load_repo_alertmanager_config()
    verify_alertmanager_config(config)


def test_verify_alertmanager_config_rejects_missing_transport() -> None:
    config = _load_repo_alertmanager_config()
    assert isinstance(config, dict)
    receivers = config["receivers"]
    assert isinstance(receivers, list)
    for receiver in receivers:
        if receiver.get("name") == "critical-receiver":
            receiver["slack_configs"] = []

    with pytest.raises(AlertmanagerVerificationError, match="critical-receiver"):
        verify_alertmanager_config(config)


def test_verify_alertmanager_config_rejects_wrong_severity_mapping() -> None:
    config = _load_repo_alertmanager_config()
    assert isinstance(config, dict)
    route = config["route"]
    assert isinstance(route, dict)
    routes = route["routes"]
    assert isinstance(routes, list)
    for child in routes:
        if child.get("match", {}).get("severity") == "critical":
            child["receiver"] = "warning-receiver"

    with pytest.raises(AlertmanagerVerificationError, match="Severity route 'critical'"):
        verify_alertmanager_config(config)


def test_main_resolves_relative_config_path_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    config_path = repo_root / "prometheus" / "alertmanager.yml"
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(alertmanager_verifier, "_repo_root", lambda: repo_root)
    captured: dict[str, object] = {}

    def _fake_load_yaml(path: Path) -> dict[str, object]:
        captured["config_path"] = path
        return {}

    monkeypatch.setattr(alertmanager_verifier, "_load_yaml", _fake_load_yaml)
    monkeypatch.setattr(alertmanager_verifier, "verify_alertmanager_config", lambda *_: None)

    assert main(["--config-path", "prometheus/alertmanager.yml"]) == 0
    assert captured["config_path"] == config_path.resolve()


def test_main_rejects_relative_config_path_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(alertmanager_verifier, "_repo_root", lambda: repo_root)

    assert main(["--config-path", "../escape/alertmanager.yml"]) == 2


def test_main_rejects_directory_config_path(tmp_path: Path) -> None:
    config_dir = tmp_path / "alertmanager-dir"
    config_dir.mkdir()

    assert main(["--config-path", str(config_dir)]) == 2
