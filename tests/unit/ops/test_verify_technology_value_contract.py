from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import scripts.verify_technology_value_contract as tvc_verifier
from scripts.verify_technology_value_contract import (
    TechnologyValueContractVerificationError,
    main,
    verify_contract_and_receipts,
)


def _load_contract_example() -> dict[str, object]:
    path = Path("contracts/examples/technology_value_contract.example.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_receipt_example() -> dict[str, object]:
    path = Path("contracts/examples/execution_receipt.example.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_verify_contract_and_receipts_accepts_repo_examples() -> None:
    verify_contract_and_receipts(
        contract_path=Path("contracts/examples/technology_value_contract.example.yaml"),
        receipt_paths=[Path("contracts/examples/execution_receipt.example.json")],
    )


def test_verify_contract_and_receipts_rejects_invalid_contract(tmp_path: Path) -> None:
    contract = _load_contract_example()
    unit_economics = contract["unit_economics"]
    assert isinstance(unit_economics, dict)
    unit_economics["primary_metric"] = {}

    contract_path = tmp_path / "technology_value_contract.yaml"
    _write_yaml(contract_path, contract)

    with pytest.raises(
        TechnologyValueContractVerificationError,
        match="contract failed schema validation at unit_economics.primary_metric",
    ):
        verify_contract_and_receipts(contract_path=contract_path)


def test_verify_contract_and_receipts_rejects_mismatched_receipt(tmp_path: Path) -> None:
    contract = _load_contract_example()
    receipt = _load_receipt_example()

    contract_path = tmp_path / "technology_value_contract.yaml"
    receipt_path = tmp_path / "execution_receipt.json"
    _write_yaml(contract_path, contract)

    data = receipt["data"]
    assert isinstance(data, dict)
    data["phase"] = "runtime"
    contract_ref = data["contract_ref"]
    assert isinstance(contract_ref, dict)
    contract_ref["name"] = "other-contract"
    _write_json(receipt_path, receipt)

    with pytest.raises(
        TechnologyValueContractVerificationError,
        match="contract_ref.name must match contract metadata.name",
    ):
        verify_contract_and_receipts(
            contract_path=contract_path,
            receipt_paths=[receipt_path],
        )


def test_main_resolves_relative_paths_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    contract_path = repo_root / "contracts/examples/technology_value_contract.example.yaml"
    receipt_path = repo_root / "contracts/examples/execution_receipt.example.json"
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(tvc_verifier, "_repo_root", lambda: repo_root)
    captured: dict[str, object] = {}

    def _fake_verify(*, contract_path: Path, receipt_paths: list[Path] | None = None) -> None:
        captured["contract_path"] = contract_path
        captured["receipt_paths"] = receipt_paths

    monkeypatch.setattr(tvc_verifier, "verify_contract_and_receipts", _fake_verify)

    assert (
        main(
            [
                "--contract-path",
                "contracts/examples/technology_value_contract.example.yaml",
                "--receipt-path",
                "contracts/examples/execution_receipt.example.json",
            ]
        )
        == 0
    )
    assert captured["contract_path"] == contract_path.resolve()
    assert captured["receipt_paths"] == [receipt_path.resolve()]


def test_main_rejects_relative_receipt_path_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tvc_verifier, "_repo_root", lambda: repo_root)

    assert (
        main(
            [
                "--contract-path",
                "contracts/examples/technology_value_contract.example.yaml",
                "--receipt-path",
                "../escape/execution_receipt.json",
            ]
        )
        == 2
    )
