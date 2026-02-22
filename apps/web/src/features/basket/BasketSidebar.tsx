import { useMemo } from 'react'

import { useCreateBasket } from '../../hooks/useBasketMutations'
import { useInstrumentSearch } from '../../hooks/useInstrumentSearch'
import { REBALANCE_FREQS, WEIGHT_METHODS } from '../../lib/constants'
import { fmtBps } from '../../lib/formatters'
import { useBasketStore } from '../../stores/basketStore'

export function BasketSidebar(): JSX.Element {
    const {
        basketName,
        basketDescription,
        legs,
        searchQuery,
        config,
        setSearchQuery,
        setBasketMeta,
        addLeg,
        removeLeg,
        setConfig,
        setBasketId,
        setLegWeightOverride,
    } = useBasketStore()

    const createBasketMutation = useCreateBasket()
    const searchQueryResult = useInstrumentSearch(searchQuery)

    const canApply = useMemo(() => legs.length > 0 && !createBasketMutation.isPending, [legs.length, createBasketMutation.isPending])

    return (
        <aside className="h-full overflow-y-auto rounded-lg border border-slate-700 bg-slate-900 p-4">
            <h2 className="text-sm font-semibold text-slate-200">Basket Builder</h2>

            <div className="mt-3 space-y-2">
                <input
                    value={basketName}
                    onChange={(event) => setBasketMeta(event.target.value, basketDescription)}
                    className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                    placeholder="Basket name"
                />
                <input
                    value={basketDescription}
                    onChange={(event) => setBasketMeta(basketName, event.target.value)}
                    className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                    placeholder="Description"
                />
            </div>

            <div className="mt-4">
                <label className="text-xs text-slate-400">Instrument search</label>
                <input
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                    placeholder="AAPL"
                />

                <div className="mt-2 max-h-44 space-y-1 overflow-y-auto">
                    {searchQuery.trim().length < 2 ? (
                        <p className="text-xs text-slate-400">Type at least 2 characters to search.</p>
                    ) : null}

                    {searchQueryResult.isLoading ? (
                        <p className="text-xs text-slate-400">Searching instruments…</p>
                    ) : null}

                    {searchQueryResult.error ? (
                        <p className="text-xs text-rose-300">{searchQueryResult.error.message}</p>
                    ) : null}

                    {searchQuery.trim().length >= 2 &&
                        searchQueryResult.data &&
                        searchQueryResult.data.length === 0 ? (
                        <p className="text-xs text-slate-400">No instruments found.</p>
                    ) : null}

                    {searchQueryResult.data?.map((instrument) => (
                        <div
                            key={instrument.id}
                            className="rounded border border-slate-700 bg-slate-950 p-2 text-xs"
                        >
                            <div className="font-medium text-slate-200">{instrument.symbol}</div>
                            <div className="text-slate-400">{instrument.name ?? instrument.asset_class}</div>
                            <div className="mt-2 flex gap-2">
                                <button
                                    type="button"
                                    onClick={() => addLeg(instrument, 'long')}
                                    className="rounded bg-emerald-700 px-2 py-1 text-white"
                                >
                                    + Long
                                </button>
                                <button
                                    type="button"
                                    onClick={() => addLeg(instrument, 'short')}
                                    className="rounded bg-amber-700 px-2 py-1 text-white"
                                >
                                    + Short
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="mt-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Legs</h3>
                <div className="mt-2 space-y-2">
                    {legs.map((leg) => (
                        <div key={`${leg.instrument_id}-${leg.side}`} className="rounded border border-slate-700 p-2 text-xs">
                            <div className="flex items-center justify-between">
                                <span className="font-medium text-slate-200">
                                    {leg.instrument.symbol} · {leg.side}
                                </span>
                                <button
                                    type="button"
                                    onClick={() => removeLeg(leg.instrument_id, leg.side)}
                                    className="text-rose-300"
                                >
                                    remove
                                </button>
                            </div>
                            <input
                                type="number"
                                value={leg.weight_override ?? ''}
                                onChange={(event) => {
                                    const nextValue = event.target.value === '' ? null : Number(event.target.value)
                                    setLegWeightOverride(leg.instrument_id, leg.side, Number.isNaN(nextValue) ? null : nextValue)
                                }}
                                className="mt-2 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
                                placeholder="Manual weight override"
                            />
                        </div>
                    ))}
                </div>
            </div>

            <div className="mt-4 space-y-2 border-t border-slate-700 pt-4">
                <label className="text-xs text-slate-400">Weight method</label>
                <select
                    value={config.weight_method}
                    onChange={(event) => setConfig('weight_method', event.target.value as typeof config.weight_method)}
                    className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                >
                    {WEIGHT_METHODS.map((method) => (
                        <option key={method.value} value={method.value}>
                            {method.label}
                        </option>
                    ))}
                </select>

                <div className="grid grid-cols-2 gap-2">
                    <input
                        type="date"
                        value={config.start_date}
                        onChange={(event) => setConfig('start_date', event.target.value)}
                        className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                    />
                    <input
                        type="date"
                        value={config.end_date}
                        onChange={(event) => setConfig('end_date', event.target.value)}
                        className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                    />
                    <input
                        type="number"
                        min={0.1}
                        max={20}
                        step={0.1}
                        value={config.gross_exposure}
                        onChange={(event) => setConfig('gross_exposure', Number(event.target.value))}
                        className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                        placeholder="Gross exposure"
                    />
                    <input
                        type="number"
                        min={20}
                        max={504}
                        value={config.lookback_days}
                        onChange={(event) => setConfig('lookback_days', Number(event.target.value))}
                        className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                        placeholder="Lookback"
                    />
                </div>

                <select
                    value={config.rebalance_freq}
                    onChange={(event) => setConfig('rebalance_freq', event.target.value as typeof config.rebalance_freq)}
                    className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                >
                    {REBALANCE_FREQS.map((freq) => (
                        <option key={freq.value} value={freq.value}>
                            {freq.label}
                        </option>
                    ))}
                </select>

                <input
                    type="text"
                    value={config.benchmark_id ?? ''}
                    onChange={(event) => setConfig('benchmark_id', event.target.value || null)}
                    className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                    placeholder="Benchmark UUID (optional)"
                />

                <div className="grid grid-cols-2 gap-2 text-xs">
                    <label className="flex items-center gap-2 text-slate-300">
                        <input
                            type="checkbox"
                            checked={config.include_funding_adj}
                            onChange={(event) => setConfig('include_funding_adj', event.target.checked)}
                        />
                        Funding Adj
                    </label>
                    <label className="flex items-center gap-2 text-slate-300">
                        <input
                            type="checkbox"
                            checked={config.include_trading_costs}
                            onChange={(event) => setConfig('include_trading_costs', event.target.checked)}
                        />
                        Trading Costs
                    </label>
                </div>

                <div className="grid grid-cols-2 gap-2">
                    <input
                        type="number"
                        min={0}
                        step={0.1}
                        value={config.fee_bps}
                        onChange={(event) => setConfig('fee_bps', Number(event.target.value))}
                        className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                        title={fmtBps(config.fee_bps)}
                        placeholder="Fee bps"
                    />
                    <input
                        type="number"
                        min={0}
                        step={0.1}
                        value={config.slippage_bps}
                        onChange={(event) => setConfig('slippage_bps', Number(event.target.value))}
                        className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-slate-100"
                        title={fmtBps(config.slippage_bps)}
                        placeholder="Slippage bps"
                    />
                </div>
            </div>

            <button
                type="button"
                disabled={!canApply}
                onClick={() => {
                    createBasketMutation.mutate(
                        {
                            name: basketName,
                            description: basketDescription || null,
                            benchmark_id: config.benchmark_id ?? null,
                            legs: legs.map((leg) => ({
                                instrument_id: leg.instrument_id,
                                side: leg.side,
                                weight_override: leg.weight_override ?? null,
                            })),
                        },
                        {
                            onSuccess: (basket) => {
                                setBasketId(basket.id)
                            },
                        },
                    )
                }}
                className="mt-4 w-full rounded bg-blue-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
                {createBasketMutation.isPending ? 'Applying…' : 'Apply Basket'}
            </button>

            {createBasketMutation.error ? (
                <p className="mt-2 text-xs text-rose-300">{createBasketMutation.error.message}</p>
            ) : null}
        </aside>
    )
}
