from __future__ import annotations

from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = APP_ROOT.parent
STATIC_DIR = APP_ROOT / "static"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


def resolve_static_asset_path(asset_name: str) -> Path:
    return STATIC_DIR / asset_name


def require_static_asset(asset_name: str) -> Path:
    asset_path = resolve_static_asset_path(asset_name)
    if not asset_path.is_file():
        raise RuntimeError(f"Required static asset is missing: {asset_path}")
    return asset_path
