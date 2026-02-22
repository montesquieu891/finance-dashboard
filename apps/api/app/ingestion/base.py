from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Instrument


@dataclass(frozen=True)
class IngestionResult:
    rows_inserted: int
    status: str
    error_message: str | None = None


class BaseConnector(ABC):
    source: str

    @abstractmethod
    async def fetch_raw(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def validate(self, normalized_data: pd.DataFrame) -> None:
        raise NotImplementedError

    @abstractmethod
    async def upsert(
        self,
        session: AsyncSession,
        instrument: Instrument,
        normalized_data: pd.DataFrame,
    ) -> int:
        raise NotImplementedError
