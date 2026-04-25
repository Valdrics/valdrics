#!/usr/bin/env python3
"""Validate Technology Value Contract and execution receipt artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)
import yaml

_CONTRACT_SCHEMA_PATH = Path("contracts/schemas/technology_value_contract.schema.json")
_RECEIPT_SCHEMA_PATH = Path("contracts/schemas/execution_receipt.schema.json")


class TechnologyValueContractVerificationError(RuntimeError):
    pass


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_repo_path(path: Path, *, field_name: str) -> Path:
    try:
        return resolve_cli_path_from_root(_repo_root(), path, field_name=field_name)
    except ValueError as exc:
        raise TechnologyValueContractVerificationError(str(exc)) from exc


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    if path.exists() and not path.is_file():
        raise TechnologyValueContractVerificationError(f"{label} must be a file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TechnologyValueContractVerificationError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TechnologyValueContractVerificationError(
            f"{label} contains invalid JSON: {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise TechnologyValueContractVerificationError(f"{label} root must be an object: {path}")
    return payload


def _load_payload(path: Path, *, label: str) -> dict[str, Any]:
    if path.exists() and not path.is_file():
        raise TechnologyValueContractVerificationError(f"{label} must be a file: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TechnologyValueContractVerificationError(f"{label} not found: {path}") from exc

    suffix = path.suffix.lower()
    try:
        if suffix in {".yaml", ".yml"}:
            payload = yaml.safe_load(raw_text)
        elif suffix == ".json":
            payload = json.loads(raw_text)
        else:
            raise TechnologyValueContractVerificationError(
                f"{label} must be .yaml, .yml, or .json: {path}"
            )
    except yaml.YAMLError as exc:
        raise TechnologyValueContractVerificationError(
            f"{label} contains invalid YAML: {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise TechnologyValueContractVerificationError(
            f"{label} contains invalid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise TechnologyValueContractVerificationError(f"{label} root must be an object: {path}")
    return payload


def _load_schema(path: Path, *, label: str) -> dict[str, Any]:
    schema = _load_json(path, label=label)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # pragma: no cover - defensive
        raise TechnologyValueContractVerificationError(
            f"{label} is not a valid JSON Schema: {path}: {exc}"
        ) from exc
    return schema


def _error_path(error: Any) -> str:
    parts = [str(part) for part in error.absolute_path]
    return ".".join(parts) if parts else "<root>"


def _validate_against_schema(
    payload: dict[str, Any],
    schema: dict[str, Any],
    *,
    label: str,
) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    if not errors:
        return

    first = errors[0]
    raise TechnologyValueContractVerificationError(
        f"{label} failed schema validation at {_error_path(first)}: {first.message}"
    )


def _validate_contract_receipt_pair(
    contract: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    metadata = contract["metadata"]
    subject = contract["subject"]
    contract_ref = receipt["data"]["contract_ref"]
    receipt_subject = receipt["data"]["subject"]

    expected_name = metadata["name"]
    if receipt["subject"] != expected_name:
        raise TechnologyValueContractVerificationError(
            "receipt.subject must match contract metadata.name"
        )
    if contract_ref["name"] != expected_name:
        raise TechnologyValueContractVerificationError(
            "receipt.data.contract_ref.name must match contract metadata.name"
        )
    if contract_ref["version"] != metadata["version"]:
        raise TechnologyValueContractVerificationError(
            "receipt.data.contract_ref.version must match contract metadata.version"
        )
    if receipt_subject["system"] != subject["system"]:
        raise TechnologyValueContractVerificationError(
            "receipt.data.subject.system must match contract subject.system"
        )
    if receipt_subject["service"] != subject["service"]:
        raise TechnologyValueContractVerificationError(
            "receipt.data.subject.service must match contract subject.service"
        )
    if receipt_subject["environment"] != subject["environment"]:
        raise TechnologyValueContractVerificationError(
            "receipt.data.subject.environment must match contract subject.environment"
        )


def verify_contract_and_receipts(
    *,
    contract_path: Path,
    receipt_paths: list[Path] | None = None,
) -> None:
    root = _repo_root()
    contract_schema = _load_schema(root / _CONTRACT_SCHEMA_PATH, label="contract_schema")
    receipt_schema = _load_schema(root / _RECEIPT_SCHEMA_PATH, label="receipt_schema")

    contract = _load_payload(contract_path, label="contract")
    _validate_against_schema(contract, contract_schema, label="contract")

    for receipt_path in receipt_paths or []:
        receipt = _load_payload(receipt_path, label="receipt")
        _validate_against_schema(receipt, receipt_schema, label="receipt")
        _validate_contract_receipt_pair(contract, receipt)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Technology Value Contract manifests and execution receipts."
    )
    parser.add_argument(
        "--contract-path",
        required=True,
        help="Path to a Technology Value Contract manifest (.yaml, .yml, or .json).",
    )
    parser.add_argument(
        "--receipt-path",
        action="append",
        default=[],
        help="Optional execution receipt path. May be passed multiple times.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        contract_path = _resolve_repo_path(
            Path(str(args.contract_path)),
            field_name="contract_path",
        )
        receipt_paths = [
            _resolve_repo_path(Path(str(raw_path)), field_name="receipt_path")
            for raw_path in args.receipt_path
        ]
        verify_contract_and_receipts(
            contract_path=contract_path,
            receipt_paths=receipt_paths,
        )
    except TechnologyValueContractVerificationError as exc:
        print(f"[technology-value-contract] failed: {exc}")
        return 2

    receipt_count = len(args.receipt_path)
    print(
        "[technology-value-contract] passed: "
        f"{contract_path} ({receipt_count} receipt{'s' if receipt_count != 1 else ''})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
