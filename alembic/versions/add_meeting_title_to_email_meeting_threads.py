"""add meeting_title to email_meeting_threads

Revision ID: add_meeting_title_to_email_meeting_threads
Revises: add_email_meeting_threads
Create Date: 2025-11-30 14:20:09.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_meeting_title_to_email_meeting_threads"
down_revision: Union[str, Sequence[str], None] = "add_email_meeting_threads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add meeting_title column to email_meeting_threads table."""
    op.add_column(
        "email_meeting_threads",
        sa.Column("meeting_title", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove meeting_title column from email_meeting_threads table."""
    op.drop_column("email_meeting_threads", "meeting_title")

