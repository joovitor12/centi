"""add email_meeting_threads table

Revision ID: add_email_meeting_threads
Revises: create_recurring_appointments
Create Date: 2025-12-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "add_email_meeting_threads"
down_revision: Union[str, Sequence[str], None] = "create_recurring_appointments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create email_meeting_threads table."""
    op.create_table(
        "email_meeting_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("owner_email", sa.String(length=255), nullable=False),
        sa.Column("participant_emails", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("suggested_times", postgresql.JSONB(), nullable=True),
        sa.Column("confirmed_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True, server_default="30"),
        sa.Column("meeting_description", sa.Text(), nullable=True),
        sa.Column("last_email_id", sa.String(length=255), nullable=True),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_index(
        op.f("ix_email_meeting_threads_thread_id"),
        "email_meeting_threads",
        ["thread_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_email_meeting_threads_status"),
        "email_meeting_threads",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop email_meeting_threads table."""
    op.drop_index(
        op.f("ix_email_meeting_threads_status"),
        table_name="email_meeting_threads",
    )
    op.drop_index(
        op.f("ix_email_meeting_threads_thread_id"),
        table_name="email_meeting_threads",
    )
    op.drop_table("email_meeting_threads")
