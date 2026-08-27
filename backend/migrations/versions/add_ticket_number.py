"""Add ticket_number sequential field to incidents

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-27 05:56:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a sequence for ticket numbers starting at 1000
    op.execute("CREATE SEQUENCE IF NOT EXISTS incident_ticket_number_seq START 1000")

    # Add the column
    op.execute("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS ticket_number INTEGER")

    # Backfill existing incidents with sequential numbers (ordered by creation)
    op.execute("""
        WITH numbered AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at ASC) + 999 AS rn
            FROM incidents
            WHERE ticket_number IS NULL
        )
        UPDATE incidents SET ticket_number = numbered.rn
        FROM numbered WHERE incidents.id = numbered.id
    """)

    # Set the sequence to continue after the highest existing number
    op.execute("""
        SELECT setval('incident_ticket_number_seq', COALESCE((SELECT MAX(ticket_number) FROM incidents), 999) + 1, false)
    """)

    # Set default to use the sequence for new incidents
    op.execute("ALTER TABLE incidents ALTER COLUMN ticket_number SET DEFAULT nextval('incident_ticket_number_seq')")

    # Add unique constraint and index
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_incidents_ticket_number ON incidents(ticket_number)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_incidents_ticket_number")
    op.execute("ALTER TABLE incidents DROP COLUMN IF EXISTS ticket_number")
    op.execute("DROP SEQUENCE IF EXISTS incident_ticket_number_seq")
