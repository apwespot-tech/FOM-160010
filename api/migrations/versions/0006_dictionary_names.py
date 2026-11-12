"""case-insensitive unique names of categories and cities

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Таблица -> (прежнее ограничение, новый индекс по lower(name))
TABLES = {
    "categories": ("uq_categories_name", "uq_categories_name_lower"),
    "cities": ("uq_cities_name", "uq_cities_name_lower"),
}


def upgrade() -> None:
    conn = op.get_bind()
    for table, (constraint, index) in TABLES.items():
        duplicates = (
            conn.execute(
                sa.text(f"SELECT lower(name) FROM {table} GROUP BY lower(name) HAVING count(*) > 1")
            )
            .scalars()
            .all()
        )
        if duplicates:
            raise RuntimeError(
                f"В {table} есть названия, различающиеся только регистром: "
                f"{', '.join(duplicates)}. Переименуйте их перед миграцией."
            )
        op.drop_constraint(constraint, table, type_="unique")
        op.create_index(index, table, [sa.text("lower(name)")], unique=True)


def downgrade() -> None:
    # Под индексом lower(name) различающихся только регистром названий нет — откат проходит
    for table, (constraint, index) in TABLES.items():
        op.drop_index(index, table_name=table)
        op.create_unique_constraint(constraint, table, ["name"])
