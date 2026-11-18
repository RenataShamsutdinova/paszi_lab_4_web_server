"""add cascade delete to resource permissions

Revision ID: d64e2ea0f2d0
Revises: 061331ab0804
Create Date: 2026-11-17 15:42:52.622846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd64e2ea0f2d0'
down_revision: Union[str, Sequence[str], None] = '061331ab0804'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем старый внешний ключ
    op.drop_constraint(
        "resource_permissions_resource_id_fkey",
        "resource_permissions",
        type_="foreignkey"
    )

    # Создаём внешний ключ с каскадным удалением
    op.create_foreign_key(
        "resource_permissions_resource_id_fkey",
        "resource_permissions",
        "resources",
        ["resource_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    # Возвращаем прежнее поведение без каскадного удаления
    op.drop_constraint(
        "resource_permissions_resource_id_fkey",
        "resource_permissions",
        type_="foreignkey"
    )

    op.create_foreign_key(
        "resource_permissions_resource_id_fkey",
        "resource_permissions",
        "resources",
        ["resource_id"],
        ["id"]
    )