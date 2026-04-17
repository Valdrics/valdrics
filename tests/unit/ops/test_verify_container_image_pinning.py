from __future__ import annotations

from pathlib import Path

import pytest

import scripts.verify_container_image_pinning as image_pinning
from scripts.verify_container_image_pinning import (
    main,
    verify_container_image_pinning,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_verify_container_image_pinning_accepts_tag_digest_and_build_images(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docker-compose.test.yml",
        "\n".join(
            [
                "services:",
                "  api:",
                "    build: .",
                "    image: valdrics-api",
                "  prometheus:",
                "    image: prom/prometheus:v2.54.1",
                "  grafana:",
                "    image: grafana/grafana@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "  production-api:",
                '    image: "${REGISTRY}/valdrics-backend:${VERSION}"',
            ]
        ),
    )

    errors = verify_container_image_pinning(
        repo_root=tmp_path,
        compose_paths=(Path("docker-compose.test.yml"),),
        environment={
            "REGISTRY": "us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime",
            "VERSION": "1.2.3",
        },
    )
    assert errors == ()


def test_verify_container_image_pinning_flags_latest_tag(tmp_path: Path) -> None:
    _write(
        tmp_path / "docker-compose.test.yml",
        "\n".join(
            [
                "services:",
                "  prometheus:",
                "    image: prom/prometheus:latest",
            ]
        ),
    )

    errors = verify_container_image_pinning(
        repo_root=tmp_path,
        compose_paths=(Path("docker-compose.test.yml"),),
    )
    assert any("mutable tag 'latest'" in item for item in errors)


def test_verify_container_image_pinning_flags_latest_from_interpolation(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docker-compose.test.yml",
        "\n".join(
            [
                "services:",
                "  api:",
                '    image: "${REGISTRY:-us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime}/valdrics-backend:${VERSION:?Set VERSION}"',
            ]
        ),
    )

    errors = verify_container_image_pinning(
        repo_root=tmp_path,
        compose_paths=(Path("docker-compose.test.yml"),),
        environment={
            "REGISTRY": "us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime",
            "VERSION": "latest",
        },
    )
    assert any("mutable tag 'latest'" in item for item in errors)


def test_verify_container_image_pinning_flags_external_image_without_tag(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docker-compose.test.yml",
        "\n".join(
            [
                "services:",
                "  grafana:",
                "    image: grafana/grafana",
            ]
        ),
    )

    errors = verify_container_image_pinning(
        repo_root=tmp_path,
        compose_paths=(Path("docker-compose.test.yml"),),
    )
    assert any("immutable tag or digest" in item for item in errors)


def test_verify_container_image_pinning_flags_invalid_digest(tmp_path: Path) -> None:
    _write(
        tmp_path / "docker-compose.test.yml",
        "\n".join(
            [
                "services:",
                "  grafana:",
                "    image: grafana/grafana@sha256:bad",
            ]
        ),
    )

    errors = verify_container_image_pinning(
        repo_root=tmp_path,
        compose_paths=(Path("docker-compose.test.yml"),),
    )
    assert any("digest must be sha256:<64-hex>" in item for item in errors)


def test_verify_container_image_pinning_flags_unresolved_required_variable(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docker-compose.test.yml",
        "\n".join(
            [
                "services:",
                "  api:",
                '    image: "${REGISTRY:-us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime}/valdrics-backend:${VERSION:?Set VERSION to an immutable release tag}"',
            ]
        ),
    )

    errors = verify_container_image_pinning(
        repo_root=tmp_path,
        compose_paths=(Path("docker-compose.test.yml"),),
        environment={"REGISTRY": "us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime"},
    )
    assert any("Set VERSION to an immutable release tag" in item for item in errors)


def test_main_returns_failure_for_missing_default_compose_files(tmp_path: Path) -> None:
    exit_code = main(["--repo-root", str(tmp_path)])
    assert exit_code == 1


def test_default_compose_paths_match_active_compose_surfaces() -> None:
    assert Path("docker-compose.yml") in image_pinning.DEFAULT_COMPOSE_PATHS
    assert Path("docker-compose.observability.yml") in image_pinning.DEFAULT_COMPOSE_PATHS
    assert Path("docker-compose.redis.yml") not in image_pinning.DEFAULT_COMPOSE_PATHS


def test_verify_container_image_pinning_rejects_non_directory_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-root.txt"
    repo_root.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="repo_root must be a directory"):
        verify_container_image_pinning(repo_root=repo_root)


def test_main_rejects_relative_compose_path_escape(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    assert main(["--repo-root", str(repo_root), "--compose-path", "../escape/docker-compose.yml"]) == 2


def test_main_rejects_directory_compose_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    compose_dir = repo_root / "docker-compose.yml"
    compose_dir.mkdir()

    assert main(["--repo-root", str(repo_root), "--compose-path", "docker-compose.yml"]) == 2


def test_main_resolves_default_repo_root_from_script_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[Path] = []
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(image_pinning, "_repo_root", lambda: repo)
    monkeypatch.setattr(
        image_pinning,
        "verify_container_image_pinning",
        lambda *, repo_root, compose_paths, environment=None: seen.append(repo_root) or (),
    )

    assert main([]) == 0
    assert seen == [repo]
