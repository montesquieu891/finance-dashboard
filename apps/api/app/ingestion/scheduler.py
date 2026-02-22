from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date, timedelta
from urllib import request

from sqlalchemy import select

from app.config import settings
from app.db import create_session_factory
from app.ingestion.yahoo import YahooFinanceConnector
from app.models import Instrument


def _post_slack_alert(message: str) -> None:
	webhook = settings.slack_webhook_url
	if not webhook:
		return

	payload = {
		"text": message,
	}
	data = json.dumps(payload).encode("utf-8")
	req = request.Request(
		webhook,
		data=data,
		headers={"Content-Type": "application/json"},
		method="POST",
	)
	try:
		with request.urlopen(req, timeout=10):
			return
	except Exception as exc:
		print(f"Slack alert failed: {exc}")


async def _resolve_symbols(explicit_symbols: list[str] | None) -> list[str]:
	if explicit_symbols:
		return explicit_symbols

	session_factory = create_session_factory()
	async with session_factory() as session:
		result = await session.execute(
			select(Instrument.symbol).where(Instrument.is_active.is_(True))
		)
		symbols = [row[0] for row in result.all()]
	return symbols


async def run_daily_refresh(
	symbols: list[str] | None,
	from_date: date,
	to_date: date,
) -> None:
	connector = YahooFinanceConnector()
	resolved_symbols = await _resolve_symbols(symbols)

	failures: list[tuple[str, str]] = []
	for symbol in resolved_symbols:
		result = await connector.ingest_instrument(
			symbol=symbol,
			start_date=from_date,
			end_date=to_date,
		)
		print(f"{symbol}: status={result.status} rows_inserted={result.rows_inserted}")
		if result.status != "success":
			failures.append((symbol, result.error_message or "unknown error"))
		await asyncio.sleep(0.5)

	if failures:
		details = "\n".join([f"- {symbol}: {reason}" for symbol, reason in failures])
		_post_slack_alert(
			"Basket Monitor daily refresh failed for one or more instruments:\n"
			f"{details}"
		)
		raise RuntimeError("Daily refresh failed; Slack alert sent if configured.")


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Run daily ingestion refresh and alert on failure")
	parser.add_argument("--symbols", nargs="+", default=None)
	parser.add_argument("--from", dest="from_date", default=None)
	parser.add_argument("--to", dest="to_date", default=None)
	parser.add_argument("--window-days", type=int, default=3)
	return parser.parse_args()


async def _main() -> None:
	args = _parse_args()
	end_date = date.fromisoformat(args.to_date) if args.to_date else date.today()
	start_date = (
		date.fromisoformat(args.from_date)
		if args.from_date
		else end_date - timedelta(days=args.window_days)
	)
	await run_daily_refresh(args.symbols, start_date, end_date)


if __name__ == "__main__":
	asyncio.run(_main())
