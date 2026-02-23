from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from email.message import EmailMessage

import yfinance as yf  # type: ignore[import-untyped]
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # pyright: ignore[reportMissingImports]
from fastapi import WebSocket
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import create_session_factory
from app.models import AlertRule, Basket, BasketLeg, Instrument, PriceDaily
from app.schemas.live import LivePriceEnvelope, LivePriceTick

logger = logging.getLogger(__name__)


@dataclass
class _ActiveInstrument:
    basket_id: uuid.UUID
    instrument_id: uuid.UUID
    symbol: str


class LiveMonitorService:
    def __init__(self) -> None:
        self._session_factory = create_session_factory()
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._connections: dict[uuid.UUID | None, set[WebSocket]] = {}
        self._latest_by_symbol: dict[str, LivePriceTick] = {}
        self._started = False

    async def start(self) -> None:
        if self._started:
            return

        self._scheduler.add_job(
            self.refresh_live_prices,
            trigger="interval",
            seconds=settings.live_refresh_interval_seconds,
            id="live-refresh",
            max_instances=1,
            coalesce=True,
            next_run_time=None,
        )
        self._scheduler.start()
        self._started = True
        asyncio.create_task(self.refresh_live_prices())

    async def stop(self) -> None:
        if not self._started:
            return
        self._scheduler.shutdown(wait=False)
        self._started = False

    async def connect(self, websocket: WebSocket, basket_id: uuid.UUID | None) -> None:
        await websocket.accept()
        self._connections.setdefault(basket_id, set()).add(websocket)
        initial = self._current_payload(basket_id)
        if initial is not None:
            await websocket.send_json(initial.model_dump(mode="json"))

    async def disconnect(self, websocket: WebSocket, basket_id: uuid.UUID | None) -> None:
        sockets = self._connections.get(basket_id)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(basket_id, None)

    async def refresh_live_prices(self) -> None:
        async with self._session_factory() as session:
            active = await self._load_active_instruments(session)
            if not active:
                return

            latest_prices = await self._fetch_prices({item.symbol for item in active})
            if not latest_prices:
                return

            symbol_to_instrument = {item.symbol: item.instrument_id for item in active}
            await self._upsert_prices(session, symbol_to_instrument, latest_prices)
            await self._evaluate_alerts(session, latest_prices)
            await session.commit()

            basket_map: dict[uuid.UUID, list[LivePriceTick]] = {}
            for item in active:
                tick = latest_prices.get(item.symbol)
                if tick is None:
                    continue
                basket_map.setdefault(item.basket_id, []).append(tick)
                self._latest_by_symbol[item.symbol] = tick

        for basket_id, ticks in basket_map.items():
            if ticks:
                await self._broadcast(basket_id, ticks)

    def _current_payload(self, basket_id: uuid.UUID | None) -> LivePriceEnvelope | None:
        ticks = list(self._latest_by_symbol.values())
        if not ticks:
            return None
        if basket_id is not None:
            return LivePriceEnvelope(
                basket_id=basket_id,
                generated_at=datetime.now(UTC),
                data=ticks,
            )
        return LivePriceEnvelope(generated_at=datetime.now(UTC), data=ticks)

    async def _broadcast(self, basket_id: uuid.UUID, ticks: list[LivePriceTick]) -> None:
        payload = LivePriceEnvelope(
            basket_id=basket_id,
            generated_at=datetime.now(UTC),
            data=ticks,
        ).model_dump(mode="json")

        global_payload = LivePriceEnvelope(
            generated_at=datetime.now(UTC),
            data=ticks,
        ).model_dump(mode="json")

        stale: list[tuple[uuid.UUID | None, WebSocket]] = []
        for key in (basket_id, None):
            sockets = self._connections.get(key, set())
            for websocket in sockets:
                try:
                    await websocket.send_json(payload if key == basket_id else global_payload)
                except Exception:
                    stale.append((key, websocket))

        for key, websocket in stale:
            await self.disconnect(websocket, key)

    async def _load_active_instruments(self, session: AsyncSession) -> list[_ActiveInstrument]:
        result = await session.execute(
            select(BasketLeg.basket_id, BasketLeg.instrument_id, Instrument.symbol)
            .join(Instrument, BasketLeg.instrument_id == Instrument.id)
            .where(Instrument.is_active.is_(True))
        )
        return [
            _ActiveInstrument(
                basket_id=row.basket_id,
                instrument_id=row.instrument_id,
                symbol=row.symbol,
            )
            for row in result
        ]

    async def _fetch_prices(self, symbols: set[str]) -> dict[str, LivePriceTick]:
        tasks = [self._fetch_single(symbol) for symbol in symbols]
        rows = await asyncio.gather(*tasks, return_exceptions=True)
        data: dict[str, LivePriceTick] = {}
        for row in rows:
            if isinstance(row, BaseException) or row is None:
                continue
            data[row.symbol] = row
        return data

    async def _fetch_single(self, symbol: str) -> LivePriceTick | None:
        def _fetch_price() -> float | None:
            ticker = yf.Ticker(symbol)
            fast_info = getattr(ticker, "fast_info", None)
            if fast_info is not None:
                for key in ("lastPrice", "regularMarketPrice", "previousClose"):
                    value = fast_info.get(key)
                    if value is not None:
                        return float(value)
            history = ticker.history(period="2d", interval="1d", auto_adjust=True)
            if history.empty:
                return None
            return float(history["Close"].dropna().iloc[-1])

        try:
            price = await asyncio.to_thread(_fetch_price)
        except Exception:
            logger.exception("Live price fetch failed for %s", symbol)
            return None

        if price is None or price <= 0:
            return None

        return LivePriceTick(symbol=symbol, price=Decimal(str(price)), as_of=datetime.now(UTC))

    async def _upsert_prices(
        self,
        session: AsyncSession,
        symbol_to_instrument: dict[str, uuid.UUID],
        ticks: dict[str, LivePriceTick],
    ) -> None:
        today = date.today()
        for symbol, tick in ticks.items():
            instrument_id = symbol_to_instrument.get(symbol)
            if instrument_id is None:
                continue
            statement = insert(PriceDaily).values(
                instrument_id=instrument_id,
                date=today,
                px_close=tick.price,
                px_adj_close=tick.price,
                px_open=tick.price,
                px_high=tick.price,
                px_low=tick.price,
                volume=None,
            )
            statement = statement.on_conflict_do_update(
                index_elements=["instrument_id", "date"],
                set_={
                    "px_close": tick.price,
                    "px_adj_close": tick.price,
                    "px_open": tick.price,
                    "px_high": tick.price,
                    "px_low": tick.price,
                },
            )
            await session.execute(statement)

    async def _evaluate_alerts(
        self,
        session: AsyncSession,
        latest_prices: dict[str, LivePriceTick],
    ) -> None:
        result = await session.execute(
            select(AlertRule)
            .where(AlertRule.is_active.is_(True))
            .options(selectinload(AlertRule.instrument))
        )
        rules = result.scalars().all()
        now = datetime.now(UTC)

        for rule in rules:
            should_trigger = False
            observed_value = 0.0

            if rule.rule_type == "drawdown":
                observed_value = await self._current_drawdown(session, rule.basket_id)
                should_trigger = observed_value >= float(rule.threshold)
            elif rule.rule_type == "leg_stop" and rule.instrument is not None:
                observed_value = await self._adverse_move(
                    session=session,
                    basket_id=rule.basket_id,
                    instrument_id=rule.instrument.id,
                    symbol=rule.instrument.symbol,
                    latest_prices=latest_prices,
                )
                should_trigger = observed_value >= float(rule.threshold)

            if not should_trigger:
                continue

            if rule.last_triggered_at is not None:
                elapsed = now - rule.last_triggered_at
                if elapsed < timedelta(minutes=int(rule.cooldown_minutes)):
                    continue

            rule.last_triggered_at = now
            await self._send_email(rule=rule, observed_value=observed_value)

    async def _current_drawdown(self, session: AsyncSession, basket_id: uuid.UUID) -> float:
        basket = (
            (
                await session.execute(
                    select(Basket)
                    .where(Basket.id == basket_id)
                    .options(selectinload(Basket.legs).selectinload(BasketLeg.instrument))
                )
            )
            .scalars()
            .one_or_none()
        )
        if basket is None or not basket.legs:
            return 0.0

        instrument_ids = [leg.instrument_id for leg in basket.legs]
        returns_rows = (
            (
                await session.execute(
                    select(PriceDaily.instrument_id, PriceDaily.date, PriceDaily.px_close)
                    .where(PriceDaily.instrument_id.in_(instrument_ids))
                    .order_by(PriceDaily.date.asc())
                )
            )
            .all()
        )
        if not returns_rows:
            return 0.0

        by_symbol: dict[str, list[tuple[date, float]]] = {
            leg.instrument.symbol: [] for leg in basket.legs
        }
        symbol_by_id = {leg.instrument_id: leg.instrument.symbol for leg in basket.legs}

        for row in returns_rows:
            if row.instrument_id is None or row.px_close is None:
                continue
            symbol = symbol_by_id.get(row.instrument_id)
            if symbol is None:
                continue
            by_symbol[symbol].append((row.date, float(row.px_close)))

        series: dict[str, dict[date, float]] = {}
        for symbol, rows in by_symbol.items():
            if len(rows) < 2:
                return 0.0
            symbol_returns: dict[date, float] = {}
            for index in range(1, len(rows)):
                prev = rows[index - 1][1]
                curr = rows[index][1]
                if prev <= 0:
                    continue
                symbol_returns[rows[index][0]] = (curr / prev) - 1.0
            series[symbol] = symbol_returns

        common_date_sets = [set(values.keys()) for values in series.values()]
        if not common_date_sets:
            return 0.0

        common_dates = set.intersection(*common_date_sets)
        if not common_dates:
            return 0.0

        weights = self._model_weights(basket.legs)
        cumulative = 1.0
        peak = 1.0
        max_drawdown = 0.0

        for row_date in sorted(common_dates):
            basket_return = 0.0
            for leg in basket.legs:
                symbol = leg.instrument.symbol
                leg_return = series[symbol].get(row_date, 0.0)
                basket_return += weights[symbol] * leg_return

            cumulative *= 1.0 + basket_return
            peak = max(peak, cumulative)
            if peak > 0:
                drawdown = (peak - cumulative) / peak
                max_drawdown = max(max_drawdown, drawdown)

        return float(max_drawdown)

    async def _adverse_move(
        self,
        session: AsyncSession,
        basket_id: uuid.UUID,
        instrument_id: uuid.UUID,
        symbol: str,
        latest_prices: dict[str, LivePriceTick],
    ) -> float:
        side_result = await session.execute(
            select(BasketLeg.side)
            .where(
                and_(
                    BasketLeg.basket_id == basket_id,
                    BasketLeg.instrument_id == instrument_id,
                )
            )
            .limit(1)
        )
        side = side_result.scalar_one_or_none()
        if side is None:
            return 0.0

        latest = latest_prices.get(symbol)
        if latest is None:
            return 0.0

        prev_close_result = await session.execute(
            select(PriceDaily.px_close)
            .where(
                PriceDaily.instrument_id == instrument_id,
                PriceDaily.date < date.today(),
            )
            .order_by(PriceDaily.date.desc())
            .limit(1)
        )
        prev_close = prev_close_result.scalar_one_or_none()
        if prev_close is None or prev_close <= 0:
            return 0.0

        move = (float(latest.price) / float(prev_close)) - 1.0
        if side == "long":
            return max(0.0, -move)
        return max(0.0, move)

    def _model_weights(self, legs: list[BasketLeg]) -> dict[str, float]:
        if not legs:
            return {}

        has_overrides = all(leg.weight_override is not None for leg in legs)
        if has_overrides:
            override_values = [
                abs(float(leg.weight_override))
                for leg in legs
                if leg.weight_override is not None
            ]
            gross = sum(override_values)
            gross = gross if gross > 0 else 1.0
            weighted: dict[str, float] = {}
            for leg in legs:
                if leg.weight_override is None:
                    continue
                weighted[leg.instrument.symbol] = (
                    float(leg.weight_override) / gross
                ) * (1.0 if leg.side == "long" else -1.0)
            return {
                symbol: value for symbol, value in weighted.items()
            }

        base_weight = 1.0 / len(legs)
        return {
            leg.instrument.symbol: base_weight * (1.0 if leg.side == "long" else -1.0)
            for leg in legs
        }

    async def _send_email(self, rule: AlertRule, observed_value: float) -> None:
        if (
            settings.smtp_host is None
            or settings.smtp_from_email is None
            or settings.smtp_to_email is None
        ):
            logger.warning("Alert triggered but SMTP is not configured: %s", rule.name)
            return

        message = EmailMessage()
        message["Subject"] = f"[Basket Monitor] Alert triggered: {rule.name}"
        message["From"] = settings.smtp_from_email
        message["To"] = settings.smtp_to_email
        message.set_content(
            "\n".join(
                [
                    f"Rule: {rule.name}",
                    f"Type: {rule.rule_type}",
                    f"Threshold: {rule.threshold}",
                    f"Observed: {observed_value:.6f}",
                    f"Basket ID: {rule.basket_id}",
                    f"Triggered at: {datetime.now(UTC).isoformat()}",
                ]
            )
        )

        await asyncio.to_thread(self._deliver_email, message)

    def _deliver_email(self, message: EmailMessage) -> None:
        if settings.smtp_host is None:
            return

        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls(context=context)
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)


live_monitor_service = LiveMonitorService()
