"""add google calendar event id

Revision ID: 8560f5db2791
Revises: add_google_calendar_event_id
Create Date: 2025-11-26 20:42:02.683667

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8560f5db2791'
down_revision: Union[str, Sequence[str], None] = 'add_google_calendar_event_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add google_calendar_event_id column to appointments table."""
    # Add column to store Google Calendar event ID (nullable for backwards compatibility)
    op.add_column(
        "appointments",
        sa.Column("google_calendar_event_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Remove google_calendar_event_id column from appointments table."""
    op.drop_column("appointments", "google_calendar_event_id")
