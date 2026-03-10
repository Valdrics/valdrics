from __future__ import annotations

from types import SimpleNamespace

from app.shared.db.migration_context import build_migration_context_kwargs


def test_build_migration_context_kwargs_enables_batch_mode_for_sqlite() -> None:
    connection = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

    kwargs = build_migration_context_kwargs(
        connection=connection,
        target_metadata="meta",
        include_object="include",
        compare_type="compare",
    )

    assert kwargs["render_as_batch"] is True
    assert kwargs["connection"] is connection


def test_build_migration_context_kwargs_skips_batch_mode_for_postgres() -> None:
    connection = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    kwargs = build_migration_context_kwargs(
        connection=connection,
        target_metadata="meta",
        include_object="include",
        compare_type="compare",
    )

    assert "render_as_batch" not in kwargs
