from __future__ import annotations

from pathlib import Path

from scripts.verify_python_module_size_budget import (
    PREFERRED_MAX_LINES,
    collect_module_size_cluster_signals,
    collect_module_size_preferred_breaches,
    collect_module_size_violations,
    main,
)


def _write_lines(path: Path, line_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"line_{idx}" for idx in range(line_count))
    path.write_text(body, encoding="utf-8")


def test_collect_module_size_violations_uses_default_budget(tmp_path: Path) -> None:
    _write_lines(tmp_path / "app/small.py", 10)
    _write_lines(tmp_path / "app/large.py", 1200)

    violations = collect_module_size_violations(tmp_path, default_max_lines=1000)
    assert [item.path for item in violations] == ["app/large.py"]


def test_collect_module_size_violations_honors_overrides(tmp_path: Path) -> None:
    _write_lines(tmp_path / "app/big.py", 1200)

    violations = collect_module_size_violations(
        tmp_path,
        default_max_lines=1000,
        overrides={"app/big.py": 1300},
    )
    assert violations == ()


def test_collect_module_size_violations_does_not_allow_lower_override(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "app/near_limit.py", 650)

    violations = collect_module_size_violations(
        tmp_path,
        default_max_lines=700,
        overrides={"app/near_limit.py": 500},
    )
    assert violations == ()


def test_main_returns_failure_when_any_module_exceeds_budget(tmp_path: Path) -> None:
    _write_lines(tmp_path / "app/too_big.py", 1100)
    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "--default-max-lines",
                "1000",
                "--enforcement-mode",
                "strict",
            ]
        )
        == 1
    )


def test_main_returns_failure_by_default_with_hard_budget_breach(
    tmp_path: Path,
    capsys,
) -> None:
    _write_lines(tmp_path / "app/too_big.py", 1100)
    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--default-max-lines",
            "1000",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 1
    assert "mode=strict" in captured
    assert "FAILED found 1 module(s) above hard budget" in captured


def test_main_returns_success_in_advisory_mode_with_hard_budget_breach(
    tmp_path: Path,
    capsys,
) -> None:
    _write_lines(tmp_path / "app/too_big.py", 1100)
    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--default-max-lines",
            "1000",
            "--enforcement-mode",
            "advisory",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "mode=advisory" in captured
    assert "advisory mode is explicitly non-blocking" in captured


def test_collect_module_size_preferred_breaches_flags_warning_paths(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "app/within.py", PREFERRED_MAX_LINES)
    _write_lines(tmp_path / "app/above.py", PREFERRED_MAX_LINES + 1)

    breaches = collect_module_size_preferred_breaches(
        tmp_path,
        preferred_max_lines=PREFERRED_MAX_LINES,
    )
    assert [item.path for item in breaches] == ["app/above.py"]


def test_main_returns_success_with_preferred_warnings(
    tmp_path: Path,
    capsys,
) -> None:
    _write_lines(tmp_path / "app/above_preferred.py", 450)
    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--default-max-lines",
            "500",
            "--preferred-max-lines",
            "400",
            "--emit-preferred-signals",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "warning found 1 module(s) above preferred target" in captured


def test_main_skips_preferred_warning_by_default(
    tmp_path: Path,
    capsys,
) -> None:
    _write_lines(tmp_path / "app/above_preferred.py", 450)
    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--default-max-lines",
            "500",
            "--preferred-max-lines",
            "400",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "above preferred target" not in captured


def test_collect_module_size_cluster_signals_flags_near_limit_files(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "app/clustered_a.py", 495)
    _write_lines(tmp_path / "app/clustered_b.py", 500)
    _write_lines(tmp_path / "app/non_clustered.py", 490)

    signals = collect_module_size_cluster_signals(
        tmp_path,
        cluster_min_lines=495,
        cluster_max_lines=500,
    )
    assert [item.path for item in signals] == [
        "app/clustered_a.py",
        "app/clustered_b.py",
    ]


def test_main_reports_clustering_warning_in_advisory_mode(
    tmp_path: Path,
    capsys,
) -> None:
    _write_lines(tmp_path / "app/near_edge.py", 500)
    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--default-max-lines",
            "700",
            "--preferred-max-lines",
            "700",
            "--cluster-min-lines",
            "495",
            "--cluster-max-lines",
            "500",
            "--emit-cluster-signals",
            "--enforcement-mode",
            "advisory",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "clustered near line budget" in captured


def test_main_skips_cluster_warning_by_default(
    tmp_path: Path,
    capsys,
) -> None:
    _write_lines(tmp_path / "app/near_edge.py", 500)
    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--default-max-lines",
            "700",
            "--preferred-max-lines",
            "700",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "clustered near line budget" not in captured
