from __future__ import annotations

import app.models  # noqa: F401  # Ensure mapper side-effects are applied.
from app.shared.db.base import Base


def test_relationship_loader_policy_disables_lazy_select_defaults() -> None:
    offenders: list[str] = []
    for mapper in Base.registry.mappers:
        for relation in mapper.relationships:
            if relation.lazy == "select":
                offenders.append(f"{mapper.class_.__name__}.{relation.key}")

    assert offenders == []
