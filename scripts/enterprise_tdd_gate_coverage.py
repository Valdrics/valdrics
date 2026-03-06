"""Coverage parsing and verification helpers for enterprise TDD gate."""

from __future__ import annotations

import fnmatch
import re
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CoverageSubsetTotals:
    lines_valid: int = 0
    lines_covered: int = 0
    branches_valid: int = 0
    branches_covered: int = 0

    def percent(self) -> float:
        denominator = self.lines_valid + self.branches_valid
        if denominator <= 0:
            return 100.0
        numerator = self.lines_covered + self.branches_covered
        return (numerator / denominator) * 100.0


_COND_RE = re.compile(r"\((\d+)/(\d+)\)")


def _resolve_xml_class_repo_path(
    *,
    filename: str,
    source_roots: tuple[Path, ...],
    repo_root: Path,
) -> str | None:
    for source_root in source_roots:
        candidate = source_root / filename
        if candidate.exists():
            return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    return None


def _parse_condition_coverage(raw: str | None) -> tuple[int, int]:
    if not raw:
        return (0, 0)
    match = _COND_RE.search(raw)
    if not match:
        return (0, 0)
    return (int(match.group(1)), int(match.group(2)))


def compute_coverage_subset_from_xml(
    *,
    xml_path: Path,
    include_patterns: Sequence[str],
    repo_root: Path,
) -> CoverageSubsetTotals:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    source_roots = tuple(
        Path(node.text)
        for node in root.findall("./sources/source")
        if node.text
    )
    totals = CoverageSubsetTotals()

    for class_node in root.findall(".//class"):
        filename = class_node.attrib.get("filename")
        if not filename:
            continue
        repo_path = _resolve_xml_class_repo_path(
            filename=filename,
            source_roots=source_roots,
            repo_root=repo_root,
        )
        if repo_path is None:
            continue
        if not any(fnmatch.fnmatch(repo_path, pattern) for pattern in include_patterns):
            continue

        lines_parent = class_node.find("./lines")
        if lines_parent is None:
            continue
        for line_node in lines_parent.findall("./line"):
            totals.lines_valid += 1
            hits = int(line_node.attrib.get("hits", "0"))
            if hits > 0:
                totals.lines_covered += 1
            if line_node.attrib.get("branch") == "true":
                covered, valid = _parse_condition_coverage(
                    line_node.attrib.get("condition-coverage")
                )
                totals.branches_covered += covered
                totals.branches_valid += valid

    return totals


def verify_coverage_subset_from_xml(
    *,
    xml_path: Path,
    include_patterns: Sequence[str],
    fail_under: int,
    label: str,
    repo_root: Path,
) -> None:
    if not xml_path.exists():
        raise RuntimeError(f"Coverage XML artifact missing: {xml_path}")
    totals = compute_coverage_subset_from_xml(
        xml_path=xml_path,
        include_patterns=include_patterns,
        repo_root=repo_root,
    )
    if (totals.lines_valid + totals.branches_valid) <= 0:
        raise RuntimeError(
            "Coverage XML subset matched no measurable lines/branches "
            f"for include patterns: {','.join(include_patterns)}"
        )
    percent = totals.percent()
    print(
        "[enterprise-gate] xml-coverage "
        f"{label}: {percent:.1f}% "
        f"(lines={totals.lines_covered}/{totals.lines_valid}, "
        f"branches={totals.branches_covered}/{totals.branches_valid})"
    )
    if percent + 1e-9 < float(fail_under):
        raise RuntimeError(
            f"Coverage failure ({label}): {percent:.1f}% < fail-under={fail_under}"
        )


def parse_coverage_report_args(cmd: Sequence[str]) -> tuple[list[str], int] | None:
    if len(cmd) < 4 or list(cmd[:4]) != ["uv", "run", "coverage", "report"]:
        return None
    include_arg = next((arg for arg in cmd if arg.startswith("--include=")), None)
    fail_under_arg = next(
        (arg for arg in cmd if arg.startswith("--fail-under=")),
        None,
    )
    if include_arg is None or fail_under_arg is None:
        return None
    include_patterns = [
        part for part in include_arg.removeprefix("--include=").split(",") if part
    ]
    fail_under = int(fail_under_arg.removeprefix("--fail-under="))
    return (include_patterns, fail_under)
