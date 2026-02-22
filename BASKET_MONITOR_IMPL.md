# BASKET MONITOR — VIBE-CODING IMPLEMENTATION BIBLE
> Keep this open while you build. Re-read the relevant section before starting each session.

---

## 1. EXECUTIVE SUMMARY

**What is it?**
A financial basket analytics dashboard. The user defines a custom basket of instruments
(equities, ETFs, futures, FX, commodities — anything with a price series), assigns
long/short sides, selects a weighting method, and instantly sees performance, risk,
factor exposures, and correlations — back-tested over a configurable period.

**What problem does it solve?**
Traders and analysts building thematic or market-neutral baskets have no single tool
that lets them construct → weight → analyze → monitor in one flow. Existing tools
(Bloomberg BAS, Excel) require either expensive licences or painful manual work.

**Core loop:**
```
User picks instruments + sides
  → System fetches/normalizes price series
    → Analytics engine computes basket returns, weights, risk metrics
      → Dashboard renders live, with interactive controls
```

**Key quality bar:** Config change → updated chart in < 2 seconds.

---

## 2. TECH STACK

### Frontend
| Concern | Choice | Notes |
|---|---|---|
| Framework | React 18 + TypeScript (strict) | Vite for build |
| Styling | Tailwind CSS v3 | No CSS files. Use `cn()` utility |
| Charts | Recharts | Composable, works with TS |
| State (server) | TanStack Query v5 | Caching + background refetch |
| State (client) | Zustand | Basket config, UI state |
| Forms | React Hook Form + Zod | Settings sidebar, inputs |
| Date handling | date-fns | Lightweight, tree-shakeable |
| HTTP client | ky | Tiny fetch wrapper |

### Backend
| Concern | Choice | Notes |
|---|---|---|
| Runtime | Python 3.12 | Use `uv` for package management |
| Framework | FastAPI | Async, auto OpenAPI docs |
| Validation | Pydantic v2 | Request + response schemas |
| ORM | SQLAlchemy 2.0 (async) | Type-safe sessions |
| Migrations | Alembic | Never alter tables by hand |
| Analytics | pandas 2 + numpy + statsmodels | Standard quant stack |
| Task queue | APScheduler | Simple daily data refresh |
| Cache | Redis 7 | API response cache |

### Infrastructure
| Concern | Choice | Notes |
|---|---|---|
| Database | PostgreSQL 16 | Primary data store |
| Cache | Redis 7 | Shared between API and scheduler |
| Container | Docker + docker-compose | Full local parity |
| CI | GitHub Actions | Lint + type check + test on PR |
| Hosting (MVP) | Single VPS (Hetzner CX21) | $5/mo, enough for solo use |
| Reverse proxy | Caddy | Auto HTTPS, dead simple |

### Dev Tools
```
pnpm (workspaces)       Node package manager
ruff                    Python linter + formatter
mypy                    Python type checker
pytest                  Backend tests
vitest                  Frontend tests
Husky + lint-staged     Pre-commit hooks
```

---

## 3. DATABASE REQUIREMENTS

### Engine
PostgreSQL 16 — no exotic extensions needed. Enable `pg_trgm` for instrument search.

### Core Tables

```sql
-- ─── INSTRUMENTS ─────────────────────────────────────────────────────────────
CREATE TABLE instruments (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol          TEXT NOT NULL,           -- e.g. "AAPL", "ES1!", "EURUSD"
  name            TEXT,
  asset_class     TEXT NOT NULL,           -- equity | etf | future | fx | commodity | index
  exchange        TEXT,
  currency        TEXT NOT NULL DEFAULT 'USD',
  multiplier      NUMERIC DEFAULT 1,
  is_active       BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (symbol, exchange)
);

-- ─── DAILY PRICES ────────────────────────────────────────────────────────────
CREATE TABLE prices_daily (
  id              BIGSERIAL PRIMARY KEY,
  instrument_id   UUID REFERENCES instruments(id) ON DELETE CASCADE,
  date            DATE NOT NULL,
  px_open         NUMERIC,
  px_high         NUMERIC,
  px_low          NUMERIC,
  px_close        NUMERIC NOT NULL,
  px_adj_close    NUMERIC,                 -- split/dividend adjusted
  volume          BIGINT,
  UNIQUE (instrument_id, date)
);
CREATE INDEX ON prices_daily (instrument_id, date DESC);

-- ─── DAILY RETURNS ───────────────────────────────────────────────────────────
CREATE TABLE returns_daily (
  id              BIGSERIAL PRIMARY KEY,
  instrument_id   UUID REFERENCES instruments(id) ON DELETE CASCADE,
  date            DATE NOT NULL,
  simple_return   NUMERIC,                 -- (P_t - P_{t-1}) / P_{t-1}
  log_return      NUMERIC,                 -- ln(P_t / P_{t-1})
  UNIQUE (instrument_id, date)
);
CREATE INDEX ON returns_daily (instrument_id, date DESC);

-- ─── FX RATES ────────────────────────────────────────────────────────────────
CREATE TABLE fx_rates_daily (
  id              BIGSERIAL PRIMARY KEY,
  base_ccy        CHAR(3) NOT NULL,
  quote_ccy       CHAR(3) NOT NULL,
  date            DATE NOT NULL,
  rate            NUMERIC NOT NULL,
  UNIQUE (base_ccy, quote_ccy, date)
);

-- ─── UNIVERSES (saved instrument groups) ─────────────────────────────────────
CREATE TABLE universes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT UNIQUE NOT NULL,
  description     TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE universe_members (
  universe_id     UUID REFERENCES universes(id) ON DELETE CASCADE,
  instrument_id   UUID REFERENCES instruments(id) ON DELETE CASCADE,
  start_date      DATE,
  end_date        DATE,
  PRIMARY KEY (universe_id, instrument_id)
);

-- ─── BASKETS (user-defined long/short constructs) ────────────────────────────
CREATE TABLE baskets (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  description     TEXT,
  benchmark_id    UUID REFERENCES instruments(id),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE basket_legs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  basket_id       UUID REFERENCES baskets(id) ON DELETE CASCADE,
  instrument_id   UUID REFERENCES instruments(id),
  side            TEXT NOT NULL CHECK (side IN ('long', 'short')),
  weight_override NUMERIC,                 -- NULL means use weighting method
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── DATA SOURCE LOG ─────────────────────────────────────────────────────────
CREATE TABLE data_ingestion_log (
  id              BIGSERIAL PRIMARY KEY,
  source          TEXT NOT NULL,           -- e.g. "yahoo_finance", "quandl"
  instrument_id   UUID REFERENCES instruments(id),
  run_at          TIMESTAMPTZ DEFAULT NOW(),
  status          TEXT CHECK (status IN ('success', 'failed', 'partial')),
  rows_inserted   INT,
  error_message   TEXT
);
```

### Design Rules
- UUIDs for all user-facing entities (baskets, instruments). BIGSERIAL for append-only tables.
- Every `UNIQUE` constraint that involves `date` gets a composite index with `date DESC`.
- `returns_daily` is a derived table — always recomputable from `prices_daily`. Treat it as a cache.
- No computed columns in the DB. Metrics like Sharpe/drawdown live in the analytics layer.
- Use `TIMESTAMPTZ` everywhere. Store in UTC. Convert to user's TZ only at the API response layer.

---

## 4. PROJECT LAYOUT

```
basket-monitor/
│
├── apps/
│   ├── web/                          # React frontend
│   │   ├── src/
│   │   │   ├── features/
│   │   │   │   ├── basket/           # Sidebar: asset selection, settings
│   │   │   │   ├── performance/      # Equity curve, drawdown, vol tabs
│   │   │   │   ├── weights/          # Weights table, bar chart, heatmap
│   │   │   │   ├── risk/             # Risk metrics table
│   │   │   │   └── correlation/      # Correlation matrix
│   │   │   ├── components/           # Shared UI: StatCard, Tag, Select, etc.
│   │   │   ├── hooks/                # useBasket, usePerformance, useWeights, etc.
│   │   │   ├── stores/               # basketStore.ts, uiStore.ts
│   │   │   ├── lib/
│   │   │   │   ├── api.ts            # ky API client, base URL, error handling
│   │   │   │   ├── formatters.ts     # fmt%, fmtPrice, fmtDate
│   │   │   │   └── constants.ts      # ASSET_CLASSES, WEIGHT_METHODS, etc.
│   │   │   ├── types/                # Shared TypeScript types (mirroring API schemas)
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   ├── .env.example
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   └── api/                          # FastAPI backend
│       ├── app/
│       │   ├── routers/
│       │   │   ├── instruments.py    # GET /instruments/search
│       │   │   ├── baskets.py        # CRUD for baskets + legs
│       │   │   ├── performance.py    # GET /analytics/performance
│       │   │   ├── weights.py        # GET /analytics/weights
│       │   │   ├── risk.py           # GET /analytics/risk
│       │   │   └── correlation.py    # GET /analytics/correlation
│       │   ├── analytics/
│       │   │   ├── returns.py        # Return series computation
│       │   │   ├── risk.py           # Vol, Sharpe, drawdown, beta
│       │   │   ├── weights.py        # All weighting methods
│       │   │   ├── correlation.py    # Correlation matrix
│       │   │   └── factors.py        # Factor regression, attribution
│       │   ├── ingestion/
│       │   │   ├── base.py           # BaseConnector ABC
│       │   │   ├── yahoo.py          # Yahoo Finance connector
│       │   │   ├── quandl.py         # Quandl/Nasdaq Data Link
│       │   │   └── scheduler.py      # APScheduler daily refresh
│       │   ├── models/               # SQLAlchemy ORM models
│       │   ├── schemas/              # Pydantic request/response schemas
│       │   ├── db.py                 # Async engine + session factory
│       │   ├── cache.py              # Redis helpers
│       │   ├── config.py             # Settings via pydantic-settings
│       │   └── main.py               # FastAPI app, lifespan, routers
│       ├── alembic/
│       │   ├── versions/
│       │   └── env.py
│       ├── tests/
│       │   ├── conftest.py
│       │   ├── test_analytics/
│       │   └── test_routers/
│       ├── .env.example
│       └── pyproject.toml
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── .env.example                      # Root-level for docker-compose
└── README.md
```

---

## 5. DOMAIN CONCEPTS

**Instrument** — anything with a price series. Can be an equity, ETF, futures contract,
FX pair, commodity, or index. The atomic unit of the system.

**Basket** — a user-defined collection of instruments each assigned a `side` (long or short)
and optionally a manual weight. The basket is the unit of analysis.

**Leg** — one instrument inside a basket. Has a side and an optional weight override.

**Weighting method** — an algorithm that assigns a weight to each leg given historical
return data. The system supports: Equal Weight, Inverse Volatility, Inverse Correlation,
Risk Parity, Beta-Adjusted, Market Cap.

**Basket return** — the weighted sum of leg returns, where short-side returns are sign-flipped.
`basket_return_t = Σ ( w_i × side_i × r_i_t )` where `side_i ∈ {+1, -1}`.

**Gross exposure** — sum of absolute weight values. User-controlled multiplier.
At 6×, a 100k notional basket has 600k in gross exposure.

**Net exposure** — sum of signed weights. For a dollar-neutral basket, this is zero.

**Benchmark** — any instrument designated as the comparison series. Defaults to a
broad market index. Beta and VS Benchmark metrics are relative to this.

**Factor** — a return series representing a systematic risk driver (size, value, momentum,
carry, macro). Used for attribution. In the MVP, factors are proxied by ETFs.

**Universe** — a saved, named collection of instruments. Used to scope searches and
auto-populate basket candidates.

---

## 6. ENTITIES

### TypeScript (Frontend)

```typescript
// types/instrument.ts
export type AssetClass = 'equity' | 'etf' | 'future' | 'fx' | 'commodity' | 'index'

export interface Instrument {
  id: string
  symbol: string
  name: string
  assetClass: AssetClass
  exchange: string
  currency: string
}

// types/basket.ts
export type Side = 'long' | 'short'
export type WeightMethod =
  | 'equal'
  | 'inverse_vol'
  | 'inverse_corr'
  | 'risk_parity'
  | 'beta_adjusted'
  | 'market_cap'
  | 'manual'

export interface BasketLeg {
  id: string
  instrument: Instrument
  side: Side
  weightOverride?: number     // null → computed by method
}

export interface Basket {
  id: string
  name: string
  description?: string
  legs: BasketLeg[]
  benchmark?: Instrument
}

// types/analytics.ts
export interface BasketConfig {
  basketId: string
  weightMethod: WeightMethod
  grossExposure: number       // multiplier, e.g. 6
  startDate: string           // ISO date
  endDate: string
  benchmarkId?: string
  lookbackDays: number        // for vol/beta estimation
  includeFundingAdj: boolean
  includeTradingCosts: boolean
  feeBps: number
  slippageBps: number
  rebalanceFreq: 'none' | 'daily' | 'weekly' | 'monthly'
}

export interface PerformancePoint {
  date: string
  basketReturn: number        // cumulative indexed to 100
  benchmarkReturn: number
  drawdown: number
}

export interface WeightSnapshot {
  method: WeightMethod
  weights: Record<string, number>  // symbol → weight
}

export interface RiskMetrics {
  annVol: number
  sharpe: number
  maxDrawdown: number
  calmar: number
  sortino: number
  beta: number
  netExposure: number
  grossExposure: number
  fundingDrag: number
  totalReturn: number
  vsbenchmark: number
}
```

### Python (Backend Pydantic Schemas)

```python
# schemas/analytics.py
class BasketConfigRequest(BaseModel):
    basket_id: UUID
    weight_method: Literal['equal','inverse_vol','inverse_corr',
                           'risk_parity','beta_adjusted','market_cap','manual']
    gross_exposure: float = Field(1.0, gt=0, le=20)
    start_date: date
    end_date: date
    benchmark_id: UUID | None = None
    lookback_days: int = Field(90, ge=20, le=504)
    include_funding_adj: bool = True
    include_trading_costs: bool = True
    fee_bps: float = Field(4.0, ge=0)
    slippage_bps: float = Field(6.0, ge=0)
    rebalance_freq: Literal['none','daily','weekly','monthly'] = 'none'

class PerformanceResponse(BaseModel):
    series: list[PerformancePoint]
    metrics: RiskMetrics
    weights: list[WeightSnapshot]
```

---

## 7. API PATTERNS

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

```
GET    /instruments/search?q=apple&asset_class=equity&limit=20
GET    /instruments/{id}
GET    /instruments/{id}/prices?from=2024-01-01&to=2024-12-31

POST   /baskets                           # Create basket
GET    /baskets                           # List all baskets
GET    /baskets/{id}                      # Get basket + legs
PUT    /baskets/{id}                      # Update basket meta
DELETE /baskets/{id}
POST   /baskets/{id}/legs                 # Add leg
DELETE /baskets/{id}/legs/{leg_id}

POST   /analytics/performance             # Body: BasketConfigRequest
POST   /analytics/weights                 # Returns all methods side-by-side
POST   /analytics/risk                    # Returns risk metrics table
POST   /analytics/correlation             # Returns correlation matrix

GET    /universes
GET    /universes/{id}/members

GET    /health                            # { status, db, redis, data_freshness }
```

### Request/Response conventions
- All dates: ISO 8601 strings (`"2024-01-15"`)
- All numbers: plain JSON numbers, not strings
- All IDs: UUID v4 strings
- Pagination: `?limit=50&offset=0` on list endpoints
- Error shape: `{ "error": "INSTRUMENT_NOT_FOUND", "detail": "...", "status": 404 }`
- Analytics endpoints use `POST` (not `GET`) because the config payload can be large

### Authentication (MVP)
```
X-API-Key: <key>     # Required on all requests
```
Key is set via env var `API_KEY`. Single shared key for solo use. Add OAuth later.

### Caching strategy
Analytics responses are cached in Redis with key:
```
analytics:{endpoint}:{sha256(sorted(config_json))}
```
TTL: 5 minutes for live mode, 24 hours for historical-only (end_date < today).

---

## 8. COMMANDS

### Initial Setup
```bash
# Clone and install
git clone <repo> && cd basket-monitor
cp .env.example .env          # fill in your values
pnpm install                  # frontend deps

# Backend
cd apps/api
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Start all services
docker-compose up -d postgres redis
```

### Database
```bash
# Run migrations
cd apps/api
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "add_basket_tags"

# Reset local DB
docker-compose down -v && docker-compose up -d postgres redis && alembic upgrade head
```

### Development
```bash
# Start backend (from apps/api)
uvicorn app.main:app --reload --port 8000

# Start frontend (from apps/web)
pnpm dev                      # runs on :5173

# Run all tests
cd apps/api && pytest -v
cd apps/web && pnpm test

# Type check
cd apps/api && mypy app/
cd apps/web && pnpm typecheck

# Lint + format
cd apps/api && ruff check . && ruff format .
cd apps/web && pnpm lint
```

### Data Ingestion
```bash
# Seed instruments (run once)
python -m app.ingestion.seed_instruments

# Manual price refresh for specific symbols
python -m app.ingestion.yahoo --symbols AAPL MSFT SPY --from 2020-01-01

# Run scheduler manually (triggers all connectors)
python -m app.ingestion.scheduler --run-now
```

### Docker
```bash
# Build images
docker-compose build

# Full production stack
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f api
docker-compose logs -f web
```

### CI (GitHub Actions triggers)
```bash
git push origin feat/my-feature    # runs lint + typecheck + test
gh pr merge --squash               # merges to main, triggers deploy
```

---

## 9. GOTCHAS

### Data
- **Yahoo Finance rate limits.** Add a 0.5s sleep between symbol fetches. Use `yfinance`
  with `auto_adjust=True` to get split/dividend-adjusted closes automatically.
- **Survivorship bias.** If you add a stock that delisted before your start_date, the
  system will silently use partial history. Always validate date range coverage
  before computing basket metrics.
- **Different trading calendars.** US equities, European equities, futures, FX all have
  different holiday schedules. Align on the intersection of trading days before computing
  returns. A missing day is not the same as a zero return.
- **FX conversion.** If legs are in different currencies, convert all returns to the
  basket's base currency before weighting. Don't skip this; it will corrupt your PnL.
- **Futures rolls.** Continuous contracts from most free sources use backward-ratio
  adjustment. This is fine for returns but misleading for absolute price levels.

### Analytics
- **Weighting methods can return extreme weights.** Inverse correlation on a highly
  correlated universe will create weights that sum to 1 but individually are huge.
  Always apply a max weight cap (default 5× equal weight) as a safety rail.
- **Short side return sign.** Remember: for a short leg, the contribution to basket return
  is `-1 × w_i × r_i`. A common bug is forgetting the sign flip.
- **Rolling metrics need warm-up periods.** Rolling vol needs N days of data before
  it's valid. Don't display vol for the first `lookback_days` of the equity curve.
- **Sharpe with daily returns.** Annualize with `√252` for equities, `√365` for crypto.
  Be explicit in the UI which convention you're using.
- **Drawdown calculation.** Drawdown is relative to the running peak. If you compute it
  on already-cumulated index values, that's correct. If you recompute from raw returns,
  you'll get wrong results if the series doesn't start at 100.

### Frontend
- **TanStack Query keys must include the full config.** If you forget to include
  `startDate` or `lookbackDays` in the query key, users will see stale cached data
  after changing those controls.
- **Recharts ResponsiveContainer needs an explicit parent height.** If the parent div
  has `height: auto`, charts will render as 0px. Always give the wrapper a fixed height
  or `min-height`.
- **Zustand stores persist across hot reloads in dev.** Reset local state during dev
  if you change the store shape. Add a version key and wipe on mismatch.
- **Large correlation matrices re-render on every sidebar change.** Memoize with
  `useMemo` on the matrix data and `React.memo` on the cell component. Without this,
  a 20×20 matrix at 60fps feels sluggish.

### Backend
- **SQLAlchemy async sessions.** Never share a session between requests. Use the
  dependency injection pattern (`async with get_db() as db`) — one session per request.
- **Pydantic v2 breaking changes from v1.** If you copy any Pydantic code from StackOverflow,
  check the version. `orm_mode = True` is now `model_config = ConfigDict(from_attributes=True)`.
- **Alembic autogenerate won't catch everything.** It misses check constraints, custom
  indexes, and sequences. Always review the generated migration before running it.
- **APScheduler job fires on startup.** Add a `next_run_time=None` flag if you don't
  want the scheduler to immediately trigger on API startup.

---

## 10. CONSTRAINTS

### Data
- MVP: daily price data only. No intraday.
- Free tier data sources: 2 years of history max from Yahoo Finance without an account.
  For longer history, use Quandl (free tier) or FRED for macro proxies.
- Max 50 instruments per basket (UI constraint to keep correlation matrix readable).
- All instruments must have price data for the selected date range. Partial history
  instruments are rejected at config validation time.

### System
- Single-user MVP. No multi-tenancy. No user accounts beyond the API key.
- Analytics computed synchronously on request. No background job queue for analytics.
  If computation exceeds 10s, return 503 with `Retry-After` and pre-compute in background.
- No real-time streaming in MVP. Poll every 60 seconds for live price updates.

### Regulatory / Legal
- No order execution. This is a read-only analytics tool.
- If user data (basket configs, portfolios) is stored, add a privacy notice even for solo use.
- Do not redistribute raw price data. The system fetches and stores prices for your own
  internal analytics only. Check your data provider's ToS.

---

## 11. REFERENCES

### Libraries
- [Recharts docs](https://recharts.org/en-US/api) — chart component reference
- [TanStack Query v5](https://tanstack.com/query/v5/docs) — `useQuery`, `useMutation`
- [Zustand](https://zustand-demo.pmnd.rs/) — store creation patterns
- [FastAPI](https://fastapi.tiangolo.com/) — routing, dependency injection, lifespan
- [SQLAlchemy 2.0 async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [pandas](https://pandas.pydata.org/docs/) — core analytics data structure
- [yfinance](https://ranaroussi.github.io/yfinance/) — free price data connector

### Financial Concepts
- Risk Parity: Roncalli (2013), "Introduction to Risk Parity and Budgeting"
- Inverse Vol / Inv Corr weighting: standard portfolio construction, no single reference
- Maximum Drawdown: calculated as `(peak - trough) / peak` over cumulative return series
- Beta-Adjusted weighting: each leg weight ∝ 1/|β_i| so that beta contributions are equalized
- Factor attribution: OLS regression of basket returns on factor return series

### Tooling
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [ruff](https://docs.astral.sh/ruff/) — Python linter
- [Vite](https://vitejs.dev/guide/) — frontend build tool
- [docker-compose v3](https://docs.docker.com/compose/compose-file/compose-file-v3/)

---

## 12. KEY BUSINESS RULES

1. **Short legs flip the return sign.** `contribution_i = w_i × (-1) × r_i` for short legs.
   This is the most important invariant in the system. Violating it inverts all PnL.

2. **Weights always sum to gross_exposure for long legs and -gross_exposure for short legs**
   in a dollar-neutral basket. In non-neutral baskets, the signed sum equals net exposure.

3. **Gross exposure is a user-controlled multiplier.** At `gross_exposure = 6`, a $100k
   notional account has $600k in total long + short exposure. Each individual leg weight
   is scaled accordingly.

4. **Weighting methods operate on the short-side universe after sign flip.** The optimizer
   sees all legs as "assets to be held long" and the sign is applied at basket construction.

5. **The benchmark is any instrument, not a fixed index.** Users can benchmark against
   SPY, a single stock, a custom basket, or nothing. `VS Benchmark` = basket return − benchmark return.

6. **Funding drag is separate from trading PnL.** It is computed from overnight financing
   rates applied to gross exposure. If `include_funding_adj = false`, funding is excluded
   from the equity curve but still shown as a separate KPI tile.

7. **A basket config change does not mutate the basket.** Configs (date range, weight method,
   gross exposure) are ephemeral — stored in client state for the session, not in the DB.
   The DB stores the basket definition (legs + sides) only.

8. **Rebalancing incurs trading costs.** If `rebalance_freq != 'none'`, fees and slippage
   are charged on the weight delta at each rebalance date. Buy-and-hold charges costs only
   at inception.

9. **All returns are in the basket's base currency.** Default USD. FX conversion is
   mandatory for multi-currency baskets.

10. **Maximum weight cap.** No single leg may receive a weight greater than
    `5 × (gross_exposure / n_legs)` regardless of method. This is a hard safety rule.

---

## 13. KEY TECHNICAL DECISIONS

### Why POST for analytics endpoints?
The basket config object is 10+ fields. Encoding it all as query params is fragile and
creates ugly URLs. POST gives a clean JSON body and proper schema validation.

### Why computed returns table vs. computing on the fly?
The `returns_daily` table trades storage for speed. Pre-computing saves 10-50ms per
analytics request. It also makes data quality issues (gaps, spikes) explicit.

### Why Zustand for client state instead of URL params?
The basket config has ~12 fields. URL params would work but make the URL ugly and create
complexity around serialization. Zustand keeps config in memory with a clean API.
Later, serialize config to URL for shareable links.

### Why APScheduler over Celery/Prefect for MVP?
Celery + a broker is two more services. APScheduler runs in-process with the API.
Good enough for a daily price refresh job with one data source. Upgrade to Prefect
when you have multiple sources and need retries, observability, and backfills.

### Why Redis instead of in-memory cache?
In-memory cache would be reset on every API restart and can't be shared between workers.
Redis adds one container but gives persistent cache, TTL management, and shared state
when you add a second API instance later.

### Why not compute everything in the frontend with raw prices?
Analytics like rolling beta regression, risk parity optimization, and factor attribution
are computationally intensive and need more than just price data. The backend is the right
place. The frontend receives only display-ready numbers.

### Why Alembic over auto-migrate?
Auto-migrate (like Prisma or Django) guesses schema from models. For a financial DB,
you need to be explicit about what changes. Alembic gives you full control and a
reviewable migration history.

---

## 14. MAJOR RISKS

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Data source goes down or changes API | High | High | Abstract connectors; add 2nd source fallback (FRED for macro, Quandl for equities) |
| Wrong return sign on shorts | Medium | Critical | Unit test the sign convention. Integration test against known basket PnL |
| Calendar misalignment corrupts basket returns | Medium | High | Explicit trading calendar alignment step; log dropped days |
| Analytics computation too slow (>5s) | Medium | Medium | Redis cache; profile with `py-spy`; parallelize with `asyncio.gather` |
| DB grows too large for VPS | Low | Medium | Partition `prices_daily` by year; archive old data to parquet |
| Free data source rate limiting | High | Low | Add `time.sleep(0.5)` between calls; exponential backoff on 429 |
| TypeScript / Pydantic schema drift | Medium | Medium | Generate TS types from OpenAPI schema using `openapi-ts` |
| Weighting method returns extreme weights | Medium | High | Max weight cap rule; validate sum of absolute weights == gross_exposure |

---

## 15. CHECKPOINTS / STAGES

---

### ✅ STAGE 0 — Foundation (Day 1–2)
**Goal:** Running, empty shell. Nothing breaks.

```
□ Monorepo initialized (pnpm workspaces)
□ apps/web: Vite + React + TypeScript + Tailwind running on :5173
□ apps/api: FastAPI with /health endpoint running on :8000
□ docker-compose.yml: postgres + redis containers up
□ .env.example committed; .env gitignored
□ Husky pre-commit hook: ruff + eslint
□ GitHub Actions CI: runs on every PR
□ README.md: setup instructions written
```
**Exit criterion:** `docker-compose up` → both apps run with no errors.

---

### ✅ STAGE 1 — Data Layer (Week 1)
**Goal:** Instruments and prices in the database. Data is clean and queryable.

```
□ SQLAlchemy models: Instrument, PriceDaily, ReturnDaily, FXRate, IngestionLog
□ Alembic: initial migration applied; tables exist
□ BaseConnector ABC written (fetch_raw, normalize, validate, upsert)
□ YahooFinanceConnector implemented and tested
□ Seed script: 20–30 instruments across equity, ETF, FX, commodity
□ Returns computed and inserted into returns_daily after each price load
□ GET /instruments/search working with text search
□ GET /instruments/{id}/prices working
□ Data ingestion log entries written on every run
□ Unit tests for connector normalize() and validate()
```
**Exit criterion:** Query the DB, see 2 years of daily prices for AAPL. Returns match manually computed values.

---

### ✅ STAGE 2 — Analytics Engine (Week 2)
**Goal:** Core financial math works correctly. No UI yet.

```
□ analytics/returns.py: basket_returns(legs, weights, returns_df) → pd.Series
□ analytics/risk.py: vol, sharpe, max_drawdown, calmar, sortino, beta, net/gross exposure
□ analytics/weights.py: equal, inverse_vol, inverse_corr, risk_parity, beta_adjusted
□ analytics/correlation.py: pairwise_correlation(returns_df, lookback) → pd.DataFrame
□ Max weight cap enforced in all weighting methods
□ Short-side sign flip tested explicitly
□ Calendar alignment: inner join on trading dates
□ FX conversion for multi-currency baskets
□ Unit tests for every analytics function with known inputs/outputs
□ Benchmark-relative metrics: vs_benchmark, tracking_error
```
**Exit criterion:** Run a manually constructed basket (e.g., long SPY, short GLD) in a Python script. Verify total return, Sharpe, and drawdown by hand.

---

### ✅ STAGE 3 — API Layer (Week 2–3)
**Goal:** Backend fully queryable via HTTP. Frontend can build against it.

```
□ POST /baskets: create basket with legs
□ GET /baskets/{id}: return basket + legs + instrument metadata
□ POST /analytics/performance: returns equity curve + metrics
□ POST /analytics/weights: returns all methods side-by-side
□ POST /analytics/risk: returns risk metrics table
□ POST /analytics/correlation: returns correlation matrix
□ Redis caching on all analytics endpoints
□ Structured error responses (INSTRUMENT_NOT_FOUND, DATE_RANGE_TOO_SHORT, etc.)
□ API key auth middleware
□ OpenAPI docs generated and readable at /docs
□ Integration tests for every endpoint (httpx + pytest + seeded test DB)
□ Generate TypeScript types from OpenAPI: `pnpm openapi-ts`
```
**Exit criterion:** Postman/curl calls to all analytics endpoints return correct shapes. TS types match.

---

### ✅ STAGE 4 — Frontend Core (Week 3–4)
**Goal:** Working dashboard with real API data, all 4 tabs functional.

```
□ basketStore: selected instruments, sides, config (grossExposure, dates, etc.)
□ uiStore: activeTab, sidebar collapsed state
□ Sidebar: instrument search (autocomplete hitting /instruments/search)
□ Sidebar: add/remove long/short legs with tags
□ Sidebar: all config controls wired (weight method, dates, costs, etc.)
□ StatCard row: 10 KPI tiles from /analytics/performance response
□ Performance tab: equity curve + drawdown + rolling vol (real data)
□ Weights tab: weights table + bar chart + heatmap (all methods)
□ Risk tab: metrics table + rolling vol chart
□ Correlation tab: matrix with color intensity
□ Loading skeletons on all panels
□ Error boundaries on every tab
□ TanStack Query keys include full config; stale data impossible
□ Empty state UI when no basket is configured
```
**Exit criterion:** Build a basket in the UI, see real PnL and weights update instantly on every config change.

---

### ✅ STAGE 5 — Polish & Robustness (Week 4–5)
**Goal:** Production-quality UX. Nothing visually broken or confusing.

```
□ Stale data banner: if data hasn't refreshed in 24h, warn user
□ Data freshness timestamp displayed in top bar ("Data as of...")
□ Instrument search shows last price + return + asset class
□ Tooltip on every stat tile explaining the metric
□ Mobile-responsive layout (sidebar collapses on small screens)
□ All number formats consistent: %, bps, $, x
□ Chart x-axis adapts to selected date range (daily → weekly labels at 1yr+)
□ Export: download equity curve as CSV
□ Save basket to DB with name + description
□ Basket selector: load/switch between saved baskets
□ Keyboard shortcut: `Cmd+K` to open instrument search
```
**Exit criterion:** A non-technical user can navigate the dashboard without confusion. No console errors.

---

### ✅ STAGE 6 — Deployment (Week 5–6)
**Goal:** Running in production. Accessible via HTTPS.

```
□ Dockerfile for API (multi-stage build, non-root user)
□ Dockerfile for web (build → nginx static serving)
□ docker-compose.prod.yml with Caddy as reverse proxy
□ Caddy config: HTTPS with auto cert, /api/* → API, /* → web
□ GitHub Actions: on merge to main, build + push images to GHCR
□ VPS setup: docker + docker-compose installed, env vars set
□ Automated daily Postgres backup to S3-compatible object storage
□ /health endpoint checks DB + Redis + data freshness
□ Slack webhook alert if daily data refresh fails
□ Env vars documented; no secrets in repo
```
**Exit criterion:** `https://your-domain.com` loads the dashboard over HTTPS. Price refresh runs at 6am daily without intervention.

---

### 🔲 STAGE 7 — Factor Layer (Future)
**Goal:** Attribution — understand why the basket returned what it returned.

```
□ Factor definitions table (factor = ETF proxy or computed long/short)
□ Rolling OLS regression: basket returns ~ factor returns
□ Factor exposure time series chart
□ PnL attribution bar chart (factor 1 contributed X%, idiosyncratic Y%)
□ Regime map: classify periods by dominant factor (growth/inflation/risk-off)
```

---

### 🔲 STAGE 8 — Live Monitoring (Future)
**Goal:** Intraday price updates, alerts, position tracking.

```
□ WebSocket connection for live price updates (15-min delay, free tier)
□ Alert rules: notify if basket drawdown > threshold, or leg breaches stop
□ Position upload: CSV of actual positions → compare to model basket
□ Funding rate tracker for futures legs
□ P&L attribution: model vs. actual divergence
```

---

## QUICK REFERENCE CARD
> Print this or keep it at the top of your terminal.

```
Start dev:
  docker-compose up -d postgres redis
  cd apps/api && uvicorn app.main:app --reload --port 8000
  cd apps/web && pnpm dev

New migration:
  alembic revision --autogenerate -m "description"
  alembic upgrade head

Lint everything:
  cd apps/api && ruff check . && mypy app/
  cd apps/web && pnpm typecheck && pnpm lint

Run tests:
  cd apps/api && pytest -v
  cd apps/web && pnpm test

Sync TS types from API:
  cd apps/web && pnpm openapi-ts

Seed data:
  python -m app.ingestion.seed_instruments
  python -m app.ingestion.yahoo --symbols SPY GLD TLT USO --from 2020-01-01

Key invariant — NEVER forget:
  Short leg contribution = w_i × (−1) × r_i
```
