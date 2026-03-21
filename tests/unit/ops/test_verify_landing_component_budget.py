from __future__ import annotations

from pathlib import Path

import pytest

import scripts.verify_landing_component_budget as landing_budget_verifier
from scripts.verify_landing_component_budget import (
    LandingBudgetVerificationError,
    main,
    verify_landing_component_budget,
)


def test_verify_landing_component_budget_accepts_repo_state() -> None:
    summary = verify_landing_component_budget()
    assert summary["hero_lines"] <= summary["max_hero_lines"]
    assert summary["required_component_count"] >= 13


def test_verify_landing_component_budget_rejects_excessive_hero_lines(
    tmp_path: Path,
) -> None:
    hero_path = tmp_path / "LandingHero.svelte"
    hero_path.write_text("\n".join(["line"] * 220), encoding="utf-8")

    component_dir = tmp_path / "landing"
    component_dir.mkdir(parents=True)
    for name in (
        "LandingHeroCopy.svelte",
        "LandingSignalMapCard.svelte",
        "LandingRoiSimulator.svelte",
        "LandingCloudHookSection.svelte",
        "LandingWorkflowSection.svelte",
        "LandingBenefitsSection.svelte",
        "LandingPlansSection.svelte",
        "LandingPersonaSection.svelte",
        "LandingCapabilitiesSection.svelte",
        "LandingTrustSection.svelte",
        "LandingRoiPlannerCta.svelte",
        "LandingLeadCaptureSection.svelte",
        "LandingExitIntentPrompt.svelte",
        "LandingCookieConsent.svelte",
    ):
        (component_dir / name).write_text("<div />\n", encoding="utf-8")

    with pytest.raises(LandingBudgetVerificationError, match="line budget exceeded"):
        verify_landing_component_budget(
            hero_path=hero_path,
            component_dir=component_dir,
            max_hero_lines=200,
        )


def test_verify_landing_component_budget_rejects_missing_components(
    tmp_path: Path,
) -> None:
    hero_path = tmp_path / "LandingHero.svelte"
    hero_path.write_text("line\n", encoding="utf-8")

    component_dir = tmp_path / "landing"
    component_dir.mkdir(parents=True)

    with pytest.raises(LandingBudgetVerificationError, match="components missing"):
        verify_landing_component_budget(
            hero_path=hero_path,
            component_dir=component_dir,
            max_hero_lines=200,
        )


def test_verify_landing_component_budget_rejects_directory_hero_path(tmp_path: Path) -> None:
    hero_dir = tmp_path / "LandingHero.svelte"
    hero_dir.mkdir()
    component_dir = tmp_path / "landing"
    component_dir.mkdir(parents=True)

    with pytest.raises(LandingBudgetVerificationError, match="hero_path must be a file"):
        verify_landing_component_budget(
            hero_path=hero_dir,
            component_dir=component_dir,
            max_hero_lines=200,
        )


def test_verify_landing_component_budget_rejects_non_directory_component_dir(tmp_path: Path) -> None:
    hero_path = tmp_path / "LandingHero.svelte"
    hero_path.write_text("line\n", encoding="utf-8")
    component_dir = tmp_path / "landing"
    component_dir.write_text("not-a-directory\n", encoding="utf-8")

    with pytest.raises(LandingBudgetVerificationError, match="component_dir must be a directory"):
        verify_landing_component_budget(
            hero_path=hero_path,
            component_dir=component_dir,
            max_hero_lines=200,
        )


def test_main_resolves_relative_paths_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    hero_path = repo_root / "dashboard" / "src" / "lib" / "components" / "LandingHero.svelte"
    component_dir = repo_root / "dashboard" / "src" / "lib" / "components" / "landing"
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(landing_budget_verifier, "_repo_root", lambda: repo_root)
    captured: dict[str, object] = {}

    def _fake_verify_landing_component_budget(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "hero_lines": 10,
            "max_hero_lines": 800,
            "required_component_count": 14,
        }

    monkeypatch.setattr(
        landing_budget_verifier,
        "verify_landing_component_budget",
        _fake_verify_landing_component_budget,
    )

    exit_code = main(
        [
            "--hero-path",
            "dashboard/src/lib/components/LandingHero.svelte",
            "--component-dir",
            "dashboard/src/lib/components/landing",
        ]
    )

    assert exit_code == 0
    assert captured["hero_path"] == hero_path.resolve()
    assert captured["component_dir"] == component_dir.resolve()


def test_main_rejects_relative_path_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(landing_budget_verifier, "_repo_root", lambda: repo_root)

    assert (
        main(
            [
                "--hero-path",
                "../escape/LandingHero.svelte",
            ]
        )
        == 2
    )
