from __future__ import annotations

import uuid
from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PriceDaily, ReturnDaily


async def rebuild_returns_for_instrument(session: AsyncSession, instrument_id: uuid.UUID) -> int:
    result = await session.execute(
        select(
            PriceDaily.date,
            func.coalesce(PriceDaily.px_adj_close, PriceDaily.px_close).label("effective_close"),
        )
        .where(PriceDaily.instrument_id == instrument_id)
        .order_by(PriceDaily.date.asc())
    )

    rows = result.all()
    await session.execute(delete(ReturnDaily).where(ReturnDaily.instrument_id == instrument_id))

    if len(rows) < 2:
        return 0

    frame = pd.DataFrame(rows, columns=["date", "effective_close"])
    frame["simple_return"] = frame["effective_close"].astype(float).pct_change()
    frame["log_return"] = np.log(
        frame["effective_close"].astype(float) / frame["effective_close"].astype(float).shift(1)
    )
    returns_frame = frame.dropna(subset=["simple_return", "log_return"]).copy()

    for row in returns_frame.itertuples(index=False):
        session.add(
            ReturnDaily(
                instrument_id=instrument_id,
                date=row.date,
                simple_return=Decimal(str(row.simple_return)),
                log_return=Decimal(str(row.log_return)),
            )
        )

    return len(returns_frame.index)