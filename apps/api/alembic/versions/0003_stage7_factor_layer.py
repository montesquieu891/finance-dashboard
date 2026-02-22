"""stage7 factor layer

Revision ID: 0003_stage7_factor_layer
Revises: 0002_stage3_api_layer_baskets
Create Date: 2026-02-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_stage7_factor_layer"
down_revision: str | None = "0002_stage3_api_layer_baskets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "factor_definitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("code", name="uq_factor_definitions_code"),
    )

    op.execute(
        """
        INSERT INTO factor_definitions
            (code, name, category, proxy_symbol, proxy_instrument_id)
        VALUES
            (
                'MKT', 'Market Beta', 'equity', 'SPY',
                (SELECT id FROM instruments WHERE symbol = 'SPY' LIMIT 1)
            ),
            (
                'SIZE', 'Size', 'equity_style', 'IWM',
                (SELECT id FROM instruments WHERE symbol = 'IWM' LIMIT 1)
            ),
            (
                'VALUE', 'Value', 'equity_style', 'IVE',
                (SELECT id FROM instruments WHERE symbol = 'IVE' LIMIT 1)
            ),
            (
                'MOM', 'Momentum', 'equity_style', 'MTUM',
                (SELECT id FROM instruments WHERE symbol = 'MTUM' LIMIT 1)
            ),
            (
                'DEF', 'Defensive', 'macro', 'TLT',
                (SELECT id FROM instruments WHERE symbol = 'TLT' LIMIT 1)
            ),
            (
                'COMM', 'Commodities', 'macro', 'DBC',
                (SELECT id FROM instruments WHERE symbol = 'DBC' LIMIT 1)
            )
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("factor_definitions")
