from pathlib import Path

import pytest

from scripts import fix_scan_signature


OLD_SIGNATURE = """class Demo:\n    async def scan(self, session: Any) -> List[Dict[str, Any]]:\n        return []\n"""


def test_process_file_updates_signature(tmp_path: Path) -> None:
    target = tmp_path / "plugin.py"
    target.write_text(OLD_SIGNATURE, encoding="utf-8")

    replacements = fix_scan_signature.process_file(target)

    assert replacements == 1
    updated = target.read_text(encoding="utf-8")
    assert "credentials: Dict[str, str] | None = None" in updated
    assert "inventory: Any = None" in updated


def test_process_file_preserves_existing_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "plugin.py"
    target.write_text(OLD_SIGNATURE, encoding="utf-8")
    original_replace = Path.replace

    def _fail_replace(self: Path, target_path: Path) -> Path:
        if self.parent == tmp_path and self.name.startswith(".plugin."):
            raise OSError("replace failed")
        return original_replace(self, target_path)

    monkeypatch.setattr(Path, "replace", _fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        fix_scan_signature.process_file(target)

    assert target.read_text(encoding="utf-8") == OLD_SIGNATURE
    assert list(tmp_path.glob(".plugin.*.tmp")) == []


def test_main_uses_repo_root_instead_of_caller_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    plugin_dir = repo_root / "app/modules/optimization/adapters/aws/plugins"
    plugin_dir.mkdir(parents=True)
    target = plugin_dir / "plugin.py"
    target.write_text(OLD_SIGNATURE, encoding="utf-8")
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir()

    monkeypatch.setattr(fix_scan_signature, "_repo_root", lambda: repo_root)
    monkeypatch.chdir(outside_cwd)

    replacements = fix_scan_signature.main()

    assert replacements == 1
    assert "config: Any = None" in target.read_text(encoding="utf-8")
