from pathlib import Path

import pytest

from scripts.finance_committee_packet_common import write_csv


def test_write_csv_replaces_existing_file_atomically(tmp_path: Path) -> None:
    target = tmp_path / "finance.csv"
    target.write_text("old,data\n", encoding="utf-8")

    write_csv(
        target,
        [
            {"tier": "starter", "mrr": 100},
            {"tier": "growth", "mrr": 250},
        ],
    )

    assert target.read_text(encoding="utf-8") == (
        "tier,mrr\n"
        "starter,100\n"
        "growth,250\n"
    )


def test_write_csv_preserves_existing_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "finance.csv"
    target.write_text("keep,this\n", encoding="utf-8")
    original_replace = Path.replace

    def _fail_replace(self: Path, target_path: Path) -> Path:
        if self.parent == tmp_path and self.name.startswith(".finance."):
            raise OSError("disk full")
        return original_replace(self, target_path)

    monkeypatch.setattr(Path, "replace", _fail_replace)

    with pytest.raises(OSError, match="disk full"):
        write_csv(target, [{"tier": "starter", "mrr": 100}])

    assert target.read_text(encoding="utf-8") == "keep,this\n"
    assert list(tmp_path.glob(".finance.*.tmp")) == []
