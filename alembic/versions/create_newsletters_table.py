"""create newsletters table

Revision ID: create_newsletters_table
Revises: add_meeting_title_to_email_meeting_threads
Create Date: 2026-05-01 22:34:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "create_newsletters_table"
down_revision: Union[str, Sequence[str], None] = "add_meeting_title_to_email_meeting_threads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create newsletters table for builder + scheduling."""
    op.create_table(
        "newsletters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("themes", sa.JSON(), nullable=False),
        sa.Column(
            "frequency_type",
            sa.String(length=50),
            nullable=False,
            server_default="daily",
        ),
        sa.Column(
            "frequency_interval_days",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("generated_title", sa.String(length=255), nullable=True),
        sa.Column("generated_html_content", sa.Text(), nullable=True),
        sa.Column("generated_text_content", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_provider_message_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_newsletters_id"), "newsletters", ["id"], unique=False)
    op.create_index(
        op.f("ix_newsletters_user_id"), "newsletters", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_newsletters_next_run_at"), "newsletters", ["next_run_at"], unique=False
    )


def downgrade() -> None:
    """Drop newsletters table."""
    op.drop_index(op.f("ix_newsletters_next_run_at"), table_name="newsletters")
    op.drop_index(op.f("ix_newsletters_user_id"), table_name="newsletters")
    op.drop_index(op.f("ix_newsletters_id"), table_name="newsletters")
    op.drop_table("newsletters")
