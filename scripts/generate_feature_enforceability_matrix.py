#!/usr/bin/env python3
"""Generate a machine-verifiable feature enforceability matrix artifact."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.shared.core.pricing import FeatureFlag, PricingTier, get_tier_config


@dataclass(frozen=True)
class EnforceabilityEvidence:
    feature: FeatureFlag
    runtime_gated_refs: tuple[str, ...]
    all_refs: tuple[str, ...]

    @property
    def status(self) -> str:
        return "runtime_gated" if self.runtime_gated_refs else "catalog_only"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _python_files(roots: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        files.extend(sorted(path for path in root.rglob("*.py")))
    return files


def _feature_evidence_for_file(*, token: str, raw: str) -> bool:
    return token in raw


def _feature_runtime_gate_for_file(*, token: str, raw: str) -> bool:
    patterns = (
        rf"requires_feature\([^)]*{re.escape(token)}",
        rf"is_feature_enabled\([^)]*{re.escape(token)}",
        rf"require_feature_or_403\([^)]*{re.escape(token)}",
        rf"require_features_or_403\([^)]*{re.escape(token)}",
    )
    return any(re.search(pattern, raw) for pattern in patterns)


def collect_enforceability(*, repo_root: Path) -> dict[FeatureFlag, EnforceabilityEvidence]:
    files = _python_files([repo_root / "app" / "modules", repo_root / "app" / "shared"])
    collected: dict[FeatureFlag, EnforceabilityEvidence] = {}

    for feature in FeatureFlag:
        token = f"FeatureFlag.{feature.name}"
        all_refs: list[str] = []
        gated_refs: list[str] = []
        for path in files:
            raw = path.read_text(encoding="utf-8")
            if _feature_evidence_for_file(token=token, raw=raw):
                rel = path.relative_to(repo_root).as_posix()
                all_refs.append(rel)
                if _feature_runtime_gate_for_file(token=token, raw=raw):
                    gated_refs.append(rel)
        collected[feature] = EnforceabilityEvidence(
            feature=feature,
            runtime_gated_refs=tuple(sorted(set(gated_refs))),
            all_refs=tuple(sorted(set(all_refs))),
        )
    return collected


def _paid_feature_union() -> set[FeatureFlag]:
    tiers = (
        PricingTier.STARTER,
        PricingTier.GROWTH,
        PricingTier.PRO,
        PricingTier.ENTERPRISE,
    )
    union: set[FeatureFlag] = set()
    for tier in tiers:
        for feature in get_tier_config(tier).get("features", set()):
            if isinstance(feature, FeatureFlag):
                union.add(feature)
            elif isinstance(feature, str):
                try:
                    union.add(FeatureFlag(feature))
                except ValueError:
                    continue
    return union


def generate_matrix(*, repo_root: Path) -> dict[str, object]:
    evidence_map = collect_enforceability(repo_root=repo_root)
    paid_features = sorted(_paid_feature_union(), key=lambda item: item.value)

    features_payload: dict[str, dict[str, object]] = {}
    for feature in paid_features:
        evidence = evidence_map[feature]
        refs = list(evidence.runtime_gated_refs or evidence.all_refs)
        features_payload[feature.value] = {
            "status": evidence.status,
            "evidence": refs,
        }

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "paid_tiers": [
                PricingTier.STARTER.value,
                PricingTier.GROWTH.value,
                PricingTier.PRO.value,
                PricingTier.ENTERPRISE.value,
            ],
            "source_of_truth": "app/shared/core/pricing.py",
            "scanner_roots": ["app/modules", "app/shared"],
        },
        "features": features_payload,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate feature enforceability matrix from pricing + code references.",
    )
    parser.add_argument(
        "--out",
        default="docs/ops/feature_enforceability_matrix_2026-02-27.json",
        help="Output path for generated matrix JSON.",
    )
    return parser.parse_args(argv)


def _resolve_output_path(*, repo_root: Path, output: str) -> Path:
    out_path = (repo_root / str(output)).resolve()
    try:
        out_path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("out must resolve inside the repository root") from exc
    if out_path.exists() and not out_path.is_file():
        raise ValueError("out must be a file path inside the repository root")
    protected_paths = {
        Path(__file__).resolve(),
        (repo_root / "scripts" / "verify_feature_enforceability_matrix.py").resolve(),
        (repo_root / "docs" / "ops" / "feature_enforceability_matrix_2026-02-27.json").resolve(),
    }
    if out_path in protected_paths:
        raise ValueError(
            "out must not overwrite feature-enforceability source, verifier, or checked-in artifact files"
        )
    protected_roots = (
        repo_root / "app" / "modules",
        repo_root / "app" / "shared",
    )
    for protected_root in protected_roots:
        try:
            out_path.relative_to(protected_root)
        except ValueError:
            continue
        raise ValueError("out must not overwrite scanned source roots")
    return out_path


def _ensure_output_parent_dir(output_path: Path) -> None:
    current = output_path.parent
    while True:
        if current.exists():
            if not current.is_dir():
                raise ValueError(
                    f"out parent must be a directory path: {current.as_posix()}"
                )
            return
        if current == current.parent:
            return
        current = current.parent


def main(argv: list[str] | None = None) -> int:
    from scripts.verify_feature_enforceability_matrix import verify_matrix

    args = _parse_args(argv)
    repo_root = _repo_root()
    payload = generate_matrix(repo_root=repo_root)
    out_path = _resolve_output_path(repo_root=repo_root, output=str(args.out))
    _ensure_output_parent_dir(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verify_matrix(artifact_path=out_path, repo_root=repo_root)
    print(
        "Feature enforceability matrix generated: "
        f"path={out_path.relative_to(repo_root)} features={len(payload.get('features', {}))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
