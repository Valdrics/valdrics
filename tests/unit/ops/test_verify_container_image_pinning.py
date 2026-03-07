from __future__ import annotations

from pathlib import Path

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


def test_main_returns_failure_for_missing_default_compose_files(tmp_path: Path) -> None:
    exit_code = main(["--repo-root", str(tmp_path)])
    assert exit_code == 1
