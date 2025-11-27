"""create recurring_appointments table

Revision ID: create_recurring_appointments
Revises: 8560f5db2791
Create Date: 2025-11-27 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "create_recurring_appointments"
down_revision: Union[str, Sequence[str], None] = "8560f5db2791"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create recurring_appointments table."""
    op.create_table(
        "recurring_appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("start_time", sa.String(), nullable=False),
        sa.Column("end_time", sa.String(), nullable=True),
        sa.Column("recurrence_pattern", sa.String(length=50), nullable=False),
        sa.Column(
            "recurrence_interval", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("recurrence_byday", sa.String(length=100), nullable=True),
        sa.Column("recurrence_bymonthday", sa.Integer(), nullable=True),
        sa.Column("end_date", sa.String(), nullable=True),
        sa.Column("max_occurrences", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("google_calendar_event_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_recurring_appointments_id"),
        "recurring_appointments",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop recurring_appointments table."""
    op.drop_index(
        op.f("ix_recurring_appointments_id"), table_name="recurring_appointments"
    )
    op.drop_table("recurring_appointments")
