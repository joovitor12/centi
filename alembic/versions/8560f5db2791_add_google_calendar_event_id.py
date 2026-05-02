"""add google calendar event id

Revision ID: 8560f5db2791
Revises: 0e1b4a9550ad
Create Date: 2025-11-26 20:42:02.683667

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8560f5db2791'
down_revision: Union[str, Sequence[str], None] = '0e1b4a9550ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add google_calendar_event_id column to appointments table."""
    # Keep migration idempotent for databases where the column already exists.
    op.execute(
        "ALTER TABLE appointments "
        "ADD COLUMN IF NOT EXISTS google_calendar_event_id VARCHAR"
    )


def downgrade() -> None:
    """Remove google_calendar_event_id column from appointments table."""
    op.execute(
        "ALTER TABLE appointments "
        "DROP COLUMN IF EXISTS google_calendar_event_id"
    )
