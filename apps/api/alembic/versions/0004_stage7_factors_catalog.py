"""stage7 factors catalog

Revision ID: 0004_stage7_factors_catalog
Revises: 0003_stage7_factor_layer
Create Date: 2026-02-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_stage7_factors_catalog"
down_revision: str | None = "0003_stage7_factor_layer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "factors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("factor_type", sa.Text(), nullable=False),
        sa.Column("proxy_symbol", sa.Text(), nullable=False),
        sa.Column("proxy_instrument_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["proxy_instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_factors_code"),
    )

    op.execute(
        """
        INSERT INTO factors
            (code, name, category, factor_type, proxy_symbol, proxy_instrument_id, is_active)
        VALUES
            (
                'MKT', 'Market', 'equity', 'etf_proxy', 'SPY',
                (SELECT id FROM instruments WHERE symbol = 'SPY' LIMIT 1),
                TRUE
            ),
            (
                'SIZE', 'Size', 'equity_style', 'etf_proxy', 'IWM',
                (SELECT id FROM instruments WHERE symbol = 'IWM' LIMIT 1),
                TRUE
            ),
            (
                'VALUE', 'Value', 'equity_style', 'etf_proxy', 'IVE',
                (SELECT id FROM instruments WHERE symbol = 'IVE' LIMIT 1),
                TRUE
            ),
            (
                'MOM', 'Momentum', 'equity_style', 'etf_proxy', 'MTUM',
                (SELECT id FROM instruments WHERE symbol = 'MTUM' LIMIT 1),
                TRUE
            ),
            (
                'QUAL', 'Quality', 'equity_style', 'etf_proxy', 'QUAL',
                (SELECT id FROM instruments WHERE symbol = 'QUAL' LIMIT 1),
                TRUE
            ),
            (
                'LOWVOL', 'Low Volatility', 'equity_style', 'etf_proxy', 'USMV',
                (SELECT id FROM instruments WHERE symbol = 'USMV' LIMIT 1),
                TRUE
            ),
            (
                'DEF', 'Defensive', 'macro', 'etf_proxy', 'TLT',
                (SELECT id FROM instruments WHERE symbol = 'TLT' LIMIT 1),
                TRUE
            ),
            (
                'COMM', 'Commodities', 'macro', 'etf_proxy', 'DBC',
                (SELECT id FROM instruments WHERE symbol = 'DBC' LIMIT 1),
                TRUE
            )
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("factors")
