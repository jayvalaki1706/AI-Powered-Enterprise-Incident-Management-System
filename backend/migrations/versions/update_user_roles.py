"""Update user roles enum - add incident_manager and team_lead, remove manager

Revision ID: a1b2c3d4e5f6
Revises: cc0bc647c8eb
Create Date: 2026-07-16 08:58:00.000000
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "cc0bc647c8eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values to the existing userrole type
    op.execute("COMMIT")  # Commit current transaction so new enum values are available
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'INCIDENT_MANAGER'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'TEAM_LEAD'")


def downgrade() -> None:
    pass  # Cannot remove enum values in PostgreSQL
