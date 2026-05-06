from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_runtime_partition_migration_covers_managed_launch_window() -> None:
    migration = (
        REPO_ROOT
        / "migrations/versions/y1z2a3b4c5d6_add_runtime_partitions_for_release_window.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision: str | Sequence[str] | None = "x0y1z2a3b4c"' in migration
    assert "start_month = date(2026, 5, 1)" in migration
    assert "months_to_create = 24" in migration
    assert 'name_prefix="audit_logs_p"' in migration
    assert 'name_prefix="cost_records_"' in migration
    assert "CREATE TABLE IF NOT EXISTS" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
