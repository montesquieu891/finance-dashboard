import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BIGINT,
    CHAR,
    DATE,
    NUMERIC,
    TEXT,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_instruments_symbol_exchange"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    symbol: Mapped[str] = mapped_column(TEXT, nullable=False)
    name: Mapped[str | None] = mapped_column(TEXT)
    asset_class: Mapped[str] = mapped_column(TEXT, nullable=False)
    exchange: Mapped[str | None] = mapped_column(TEXT)
    currency: Mapped[str] = mapped_column(TEXT, nullable=False, server_default=text("'USD'"))
    multiplier: Mapped[Decimal | None] = mapped_column(NUMERIC, server_default=text("1"))
    is_active: Mapped[bool | None] = mapped_column(Boolean, server_default=text("TRUE"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )


class PriceDaily(Base):
    __tablename__ = "prices_daily"
    __table_args__ = (
        UniqueConstraint("instrument_id", "date", name="uq_prices_daily_instrument_date"),
        Index("ix_prices_daily_instrument_date_desc", "instrument_id", text("date DESC")),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(BIGINT, "postgresql"), primary_key=True, autoincrement=True
    )
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="CASCADE"),
    )
    date: Mapped[date] = mapped_column(DATE, nullable=False)
    px_open: Mapped[Decimal | None] = mapped_column(NUMERIC)
    px_high: Mapped[Decimal | None] = mapped_column(NUMERIC)
    px_low: Mapped[Decimal | None] = mapped_column(NUMERIC)
    px_close: Mapped[Decimal] = mapped_column(NUMERIC, nullable=False)
    px_adj_close: Mapped[Decimal | None] = mapped_column(NUMERIC)
    volume: Mapped[int | None] = mapped_column(BIGINT)


class ReturnDaily(Base):
    __tablename__ = "returns_daily"
    __table_args__ = (
        UniqueConstraint("instrument_id", "date", name="uq_returns_daily_instrument_date"),
        Index("ix_returns_daily_instrument_date_desc", "instrument_id", text("date DESC")),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(BIGINT, "postgresql"), primary_key=True, autoincrement=True
    )
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="CASCADE"),
    )
    date: Mapped[date] = mapped_column(DATE, nullable=False)
    simple_return: Mapped[Decimal | None] = mapped_column(NUMERIC)
    log_return: Mapped[Decimal | None] = mapped_column(NUMERIC)


class FXRateDaily(Base):
    __tablename__ = "fx_rates_daily"
    __table_args__ = (
        UniqueConstraint("base_ccy", "quote_ccy", "date", name="uq_fx_rates_daily_pair_date"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(BIGINT, "postgresql"), primary_key=True, autoincrement=True
    )
    base_ccy: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    quote_ccy: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    date: Mapped[date] = mapped_column(DATE, nullable=False)
    rate: Mapped[Decimal] = mapped_column(NUMERIC, nullable=False)


class IngestionLog(Base):
    __tablename__ = "data_ingestion_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'failed', 'partial')",
            name="ck_data_ingestion_log_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(BIGINT, "postgresql"), primary_key=True, autoincrement=True
    )
    source: Mapped[str] = mapped_column(TEXT, nullable=False)
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id")
    )
    run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    status: Mapped[str | None] = mapped_column(TEXT)
    rows_inserted: Mapped[int | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(TEXT)
