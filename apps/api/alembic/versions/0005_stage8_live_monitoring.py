"""stage8 live monitoring

Revision ID: 0005_stage8_live_monitoring
Revises: 0004_stage7_factors_catalog
Create Date: 2026-02-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_stage8_live_monitoring"
down_revision: str | None = "0004_stage7_factors_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("basket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("rule_type", sa.Text(), nullable=False),
        sa.Column("threshold", sa.Numeric(), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), server_default=sa.text("60"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rule_type IN ('drawdown', 'leg_stop')",
            name="ck_alert_rules_rule_type",
        ),
        sa.CheckConstraint("threshold > 0", name="ck_alert_rules_threshold_positive"),
        sa.CheckConstraint(
            "cooldown_minutes >= 1 AND cooldown_minutes <= 1440",
            name="ck_alert_rules_cooldown_minutes_range",
        ),
        sa.ForeignKeyConstraint(["basket_id"], ["baskets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "real_positions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("basket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("avg_price", sa.Numeric(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["basket_id"], ["baskets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "basket_id",
            "instrument_id",
            name="uq_real_positions_basket_instrument",
        ),
    )


def downgrade() -> None:
    op.drop_table("real_positions")
    op.drop_table("alert_rules")
