import { useEffect, useMemo, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { useBasketsQuery } from '../../hooks/useAnalyticsQueries'
import { useCreateBasket, useLoadBasket } from '../../hooks/useBasketMutations'
import { useLegIngestionStatus } from '../../hooks/useLegIngestionStatus'
import { useAlertRulesQuery, useCreateAlertRule, useDeleteAlertRule } from '../../hooks/useLiveMonitoring'
import { useInstrumentSearch } from '../../hooks/useInstrumentSearch'
import { useInstrumentSnapshots } from '../../hooks/useInstrumentSnapshots'
import { REBALANCE_FREQS, WEIGHT_METHODS } from '../../lib/constants'
import { fmtBps, fmtCurrency, fmtPct } from '../../lib/formatters'
import { useBasketStore } from '../../stores/basketStore'

interface BasketSidebarProps {
    livePricesBySymbol: Record<string, { price: number; asOf: string }>
}

export function BasketSidebar({ livePricesBySymbol }: BasketSidebarProps): JSX.Element {
    const queryClient = useQueryClient()
    const {
        basketId,
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
        loadBasket,
    } = useBasketStore()

    const createBasketMutation = useCreateBasket()
    const loadBasketMutation = useLoadBasket()
    const basketsQuery = useBasketsQuery()
    const searchQueryResult = useInstrumentSearch(searchQuery)
    const snapshotsQuery = useInstrumentSnapshots(searchQueryResult.data ?? [])
    const ingestionStatus = useLegIngestionStatus(legs)
    const alertsQuery = useAlertRulesQuery(basketId)
    const createAlertRule = useCreateAlertRule(basketId)
    const deleteAlertRule = useDeleteAlertRule(basketId)
    const previousStatusRef = useRef<Record<string, 'complete' | 'ingesting' | 'failed'>>({})

    useEffect(() => {
        ingestionStatus.statusByInstrumentId.forEach((status, instrumentId) => {
            const previousStatus = previousStatusRef.current[instrumentId]
            if (previousStatus === 'ingesting' && status === 'complete') {
                queryClient.invalidateQueries({ queryKey: ['analytics'] })
                queryClient.invalidateQueries({ queryKey: ['instrument-prices', instrumentId] })
            }
            previousStatusRef.current[instrumentId] = status
        })
    }, [ingestionStatus.statusByInstrumentId, queryClient])

    const canApply = useMemo(() => legs.length > 0 && !createBasketMutation.isPending, [legs.length, createBasketMutation.isPending])

    return (
        <aside className="h-full overflow-y-auto rounded border border-[#1a1a1a] bg-[#080808] p-4">
            <h2 className="text-sm font-semibold tracking-[0.08em] text-[#d7d7d7]">Basket Builder</h2>

            <div className="mt-3">
                <label className="ui-label">Saved baskets</label>
                <select
                    value={basketId ?? ''}
                    onChange={(event) => {
                        const selectedBasketId = event.target.value
                        if (!selectedBasketId) {
                            return
                        }
                        loadBasketMutation.mutate(selectedBasketId, {
                            onSuccess: (basket) => {
                                loadBasket(basket)
                            },
                        })
                    }}
                    className="ui-input mt-1 w-full px-2 py-1 text-sm"
                >
                    <option value="">Select basket...</option>
                    {basketsQuery.data?.map((basket) => (
                        <option key={basket.id} value={basket.id}>
                            {basket.name}
                        </option>
                    ))}
                </select>
            </div>

            <div className="mt-3 space-y-2">
                <input
                    value={basketName}
                    onChange={(event) => setBasketMeta(event.target.value, basketDescription)}
                    className="ui-input w-full px-2 py-1 text-sm"
                    placeholder="Basket name"
                />
                <input
                    value={basketDescription}
                    onChange={(event) => setBasketMeta(basketName, event.target.value)}
                    className="ui-input w-full px-2 py-1 text-sm"
                    placeholder="Description"
                />
            </div>

            <div className="mt-4">
                <label className="ui-label">Instrument search</label>
                <input
                    id="instrument-search-input"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    className="ui-input mt-1 w-full px-2 py-1 text-sm"
                    placeholder="AAPL"
                />

                <div className="mt-2 max-h-44 space-y-1 overflow-y-auto">
                    {searchQuery.trim().length < 2 ? (
                        <p className="text-xs text-[#8a8a8a]">Type at least 2 characters to search.</p>
                    ) : null}

                    {searchQueryResult.isLoading ? (
                        <p className="text-xs text-[#8a8a8a]">Searching instruments…</p>
                    ) : null}

                    {searchQuery.trim().length >= 2 && searchQueryResult.isFetching ? (
                        <p className="text-xs text-[#f5a623]">⏳ Live lookup in progress…</p>
                    ) : null}

                    {searchQueryResult.error ? (
                        <p className="text-xs text-[#ff3d5a]">{searchQueryResult.error.message}</p>
                    ) : null}

                    {searchQuery.trim().length >= 2 &&
                        searchQueryResult.data &&
                        searchQueryResult.data.length === 0 ? (
                        <p className="text-xs text-[#8a8a8a]">No instruments found.</p>
                    ) : null}

                    {searchQueryResult.data?.map((instrument) => (
                        <div
                            key={instrument.id}
                            className="rounded border border-[#1a1a1a] bg-[#050505] p-2 text-xs"
                        >
                            <div className="font-medium text-[#d7d7d7]">{instrument.symbol}</div>
                            <div className="text-[#8a8a8a]">{instrument.name ?? instrument.asset_class}</div>
                            <div className="text-[#8a8a8a]">
                                {instrument.asset_class.toUpperCase()} ·{' '}
                                {(() => {
                                    const snapshot = snapshotsQuery.snapshots.get(instrument.id)
                                    if (!snapshot || snapshot.lastPrice === null) {
                                        return '--'
                                    }
                                    return fmtCurrency(snapshot.lastPrice)
                                })()}
                                {' · '}
                                {(() => {
                                    const snapshot = snapshotsQuery.snapshots.get(instrument.id)
                                    if (!snapshot || snapshot.dailyReturn === null) {
                                        return '--'
                                    }
                                    return fmtPct(snapshot.dailyReturn)
                                })()}
                            </div>
                            <div className="mt-2 flex gap-2">
                                <button
                                    type="button"
                                    onClick={() => addLeg(instrument, 'long')}
                                    className="rounded-sm border border-[#1a1a1a] px-2 py-1 text-[#00ff9d] transition-colors duration-150 hover:bg-[#0d0d0d]"
                                >
                                    + Long
                                </button>
                                <button
                                    type="button"
                                    onClick={() => addLeg(instrument, 'short')}
                                    className="rounded-sm border border-[#1a1a1a] px-2 py-1 text-[#ff3d5a] transition-colors duration-150 hover:bg-[#0d0d0d]"
                                >
                                    + Short
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="mt-4">
                <h3 className="ui-label font-semibold">Legs</h3>
                <div className="mt-2 space-y-2">
                    {legs.map((leg) => (
                        <div key={`${leg.instrument_id}-${leg.side}`} className="rounded border border-[#1a1a1a] bg-[#050505] p-2 text-xs">
                            <div className="flex items-center justify-between">
                                <span className={`font-medium ${leg.side === 'long' ? 'text-[#00ff9d]' : 'text-[#ff3d5a]'}`}>
                                    {leg.instrument.symbol} · {leg.side}
                                </span>
                                <button
                                    type="button"
                                    onClick={() => removeLeg(leg.instrument_id, leg.side)}
                                    className="text-[#ff3d5a]"
                                >
                                    remove
                                </button>
                            </div>
                            <div className="mt-1 flex items-center justify-between text-[#8a8a8a]">
                                <span>Live</span>
                                <span className="inline-flex items-center gap-1">
                                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#00ff9d]" />
                                    {(() => {
                                        const live = livePricesBySymbol[leg.instrument.symbol]
                                        if (!live) {
                                            return '--'
                                        }
                                        return fmtCurrency(live.price)
                                    })()}
                                </span>
                            </div>
                            <input
                                type="number"
                                value={leg.weight_override ?? ''}
                                onChange={(event) => {
                                    const nextValue = event.target.value === '' ? null : Number(event.target.value)
                                    setLegWeightOverride(leg.instrument_id, leg.side, Number.isNaN(nextValue) ? null : nextValue)
                                }}
                                className="ui-input mt-2 w-full px-2 py-1"
                                placeholder="Manual weight override"
                            />

                            {(() => {
                                const status = ingestionStatus.statusByInstrumentId.get(leg.instrument_id)
                                if (status === 'ingesting') {
                                    return <p className="mt-2 text-xs text-[#f5a623]">Fetching price history...</p>
                                }
                                if (status === 'failed') {
                                    return <p className="mt-2 text-xs text-[#ff3d5a]">Price ingestion failed.</p>
                                }
                                return null
                            })()}
                        </div>
                    ))}
                </div>
            </div>

            {ingestionStatus.hasPolling ? <p className="mt-2 text-xs text-[#8a8a8a]">Polling ingestion status every 3s…</p> : null}

            <div className="mt-4 rounded border border-[#1a1a1a] bg-[#050505] p-3">
                <details>
                    <summary className="cursor-pointer text-xs font-semibold tracking-[0.06em] text-[#d7d7d7]">
                        Alerts
                    </summary>

                    <div className="mt-3 space-y-2">
                        <button
                            type="button"
                            disabled={!basketId || createAlertRule.isPending}
                            onClick={() => {
                                createAlertRule.mutate({
                                    name: 'Basket drawdown 8%',
                                    rule_type: 'drawdown',
                                    threshold: 0.08,
                                    cooldown_minutes: 60,
                                    is_active: true,
                                })
                            }}
                            className="w-full rounded-sm border border-[#1a1a1a] bg-[#080808] px-2 py-1 text-left text-xs text-[#f5a623] transition-colors duration-150 hover:bg-[#0d0d0d] disabled:opacity-50"
                        >
                            + Add drawdown alert (8%)
                        </button>

                        <button
                            type="button"
                            disabled={!basketId || legs.length === 0 || createAlertRule.isPending}
                            onClick={() => {
                                const firstLeg = legs[0]
                                if (!firstLeg) {
                                    return
                                }
                                createAlertRule.mutate({
                                    name: `${firstLeg.instrument.symbol} stop 3%`,
                                    rule_type: 'leg_stop',
                                    threshold: 0.03,
                                    cooldown_minutes: 60,
                                    is_active: true,
                                    instrument_id: firstLeg.instrument_id,
                                })
                            }}
                            className="w-full rounded-sm border border-[#1a1a1a] bg-[#080808] px-2 py-1 text-left text-xs text-[#ff3d5a] transition-colors duration-150 hover:bg-[#0d0d0d] disabled:opacity-50"
                        >
                            + Add leg stop alert (first leg)
                        </button>

                        {alertsQuery.isLoading ? <p className="text-xs text-[#8a8a8a]">Loading alerts…</p> : null}
                        {alertsQuery.error ? <p className="text-xs text-[#ff3d5a]">{alertsQuery.error.message}</p> : null}

                        {alertsQuery.data?.map((rule) => (
                            <div key={rule.id} className="rounded border border-[#1a1a1a] bg-[#080808] p-2 text-xs">
                                <div className="flex items-start justify-between gap-2">
                                    <div>
                                        <p className="font-medium text-[#d7d7d7]">{rule.name}</p>
                                        <p className="text-[#8a8a8a]">
                                            {rule.rule_type} · threshold {fmtPct(Number(rule.threshold))} · cooldown {rule.cooldown_minutes}m
                                        </p>
                                        <p className="text-[#8a8a8a]">
                                            Last trigger: {rule.last_triggered_at ? new Date(rule.last_triggered_at).toLocaleString() : 'Never'}
                                        </p>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => deleteAlertRule.mutate(rule.id)}
                                        className="text-[#ff3d5a]"
                                    >
                                        remove
                                    </button>
                                </div>
                            </div>
                        ))}

                        {alertsQuery.data && alertsQuery.data.length === 0 ? (
                            <p className="text-xs text-[#8a8a8a]">No alert rules configured.</p>
                        ) : null}
                    </div>
                </details>
            </div>

            <div className="mt-4 space-y-2 border-t border-[#1a1a1a] pt-4">
                <label className="ui-label">Weight method</label>
                <select
                    value={config.weight_method}
                    onChange={(event) => setConfig('weight_method', event.target.value as typeof config.weight_method)}
                    className="ui-input w-full px-2 py-1 text-sm"
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
                        className="ui-input px-2 py-1 text-sm"
                    />
                    <input
                        type="date"
                        value={config.end_date}
                        onChange={(event) => setConfig('end_date', event.target.value)}
                        className="ui-input px-2 py-1 text-sm"
                    />
                    <input
                        type="number"
                        min={0.1}
                        max={20}
                        step={0.1}
                        value={config.gross_exposure}
                        onChange={(event) => setConfig('gross_exposure', Number(event.target.value))}
                        className="ui-input px-2 py-1 text-sm"
                        placeholder="Gross exposure"
                    />
                    <input
                        type="number"
                        min={20}
                        max={504}
                        value={config.lookback_days}
                        onChange={(event) => setConfig('lookback_days', Number(event.target.value))}
                        className="ui-input px-2 py-1 text-sm"
                        placeholder="Lookback"
                    />
                </div>

                <select
                    value={config.rebalance_freq}
                    onChange={(event) => setConfig('rebalance_freq', event.target.value as typeof config.rebalance_freq)}
                    className="ui-input w-full px-2 py-1 text-sm"
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
                    className="ui-input w-full px-2 py-1 text-sm"
                    placeholder="Benchmark UUID (optional)"
                />

                <div className="grid grid-cols-2 gap-2 text-xs">
                    <label className="flex items-center gap-2 text-[#d7d7d7]">
                        <input
                            type="checkbox"
                            checked={config.include_funding_adj}
                            onChange={(event) => setConfig('include_funding_adj', event.target.checked)}
                            className="accent-[#00ff9d]"
                        />
                        Funding Adj
                    </label>
                    <label className="flex items-center gap-2 text-[#d7d7d7]">
                        <input
                            type="checkbox"
                            checked={config.include_trading_costs}
                            onChange={(event) => setConfig('include_trading_costs', event.target.checked)}
                            className="accent-[#00ff9d]"
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
                        className="ui-input px-2 py-1 text-sm"
                        title={fmtBps(config.fee_bps)}
                        placeholder="Fee bps"
                    />
                    <input
                        type="number"
                        min={0}
                        step={0.1}
                        value={config.slippage_bps}
                        onChange={(event) => setConfig('slippage_bps', Number(event.target.value))}
                        className="ui-input px-2 py-1 text-sm"
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
                className="mt-4 w-full rounded-sm border border-[#1a1a1a] bg-[#050505] px-3 py-2 text-sm font-semibold text-[#00ff9d] transition-colors duration-150 hover:bg-[#0d0d0d] disabled:opacity-50"
            >
                {createBasketMutation.isPending ? 'Applying…' : 'Apply Basket'}
            </button>

            {createBasketMutation.error ? (
                <p className="mt-2 text-xs text-[#ff3d5a]">{createBasketMutation.error.message}</p>
            ) : null}

            {loadBasketMutation.error ? (
                <p className="mt-2 text-xs text-[#ff3d5a]">{loadBasketMutation.error.message}</p>
            ) : null}
        </aside>
    )
}
