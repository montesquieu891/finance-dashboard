"""stage1 data layer

Revision ID: 0001_stage1_data_layer
Revises:
Create Date: 2026-02-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_stage1_data_layer"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("asset_class", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("multiplier", sa.Numeric(), server_default=sa.text("1"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "exchange"),
    )

    op.create_table(
        "prices_daily",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("px_open", sa.Numeric(), nullable=True),
        sa.Column("px_high", sa.Numeric(), nullable=True),
        sa.Column("px_low", sa.Numeric(), nullable=True),
        sa.Column("px_close", sa.Numeric(), nullable=False),
        sa.Column("px_adj_close", sa.Numeric(), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instrument_id", "date"),
    )
    op.create_index(
        "ix_prices_daily_instrument_date_desc",
        "prices_daily",
        ["instrument_id", sa.text("date DESC")],
        unique=False,
    )

    op.create_table(
        "returns_daily",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("simple_return", sa.Numeric(), nullable=True),
        sa.Column("log_return", sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instrument_id", "date"),
    )
    op.create_index(
        "ix_returns_daily_instrument_date_desc",
        "returns_daily",
        ["instrument_id", sa.text("date DESC")],
        unique=False,
    )

    op.create_table(
        "fx_rates_daily",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("base_ccy", sa.CHAR(length=3), nullable=False),
        sa.Column("quote_ccy", sa.CHAR(length=3), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("rate", sa.Numeric(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("base_ccy", "quote_ccy", "date"),
    )

    op.create_table(
        "data_ingestion_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("rows_inserted", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('success', 'failed', 'partial')"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("data_ingestion_log")
    op.drop_table("fx_rates_daily")
    op.drop_index("ix_returns_daily_instrument_date_desc", table_name="returns_daily")
    op.drop_table("returns_daily")
    op.drop_index("ix_prices_daily_instrument_date_desc", table_name="prices_daily")
    op.drop_table("prices_daily")
    op.drop_table("instruments")
