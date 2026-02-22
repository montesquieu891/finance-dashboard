import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'
import { useQueryClient } from '@tanstack/react-query'

import { ErrorBoundary } from '../../components/ErrorBoundary'
import { LoadingSkeleton } from '../../components/LoadingSkeleton'
import { StatCard } from '../../components/StatCard'
import { useFactorsQuery, usePerformanceQuery } from '../../hooks/useAnalyticsQueries'
import { buildXAxisFormatter, diffDays, fmtDate, fmtMultiple, fmtPct } from '../../lib/formatters'
import type { BasketConfig, PerformanceResponse } from '../../types/domain'

interface PerformanceTabProps {
    config: BasketConfig
}

const formatTooltipLabel = (label: unknown): string =>
    typeof label === 'string' ? fmtDate(label) : String(label)

const rollingVol = (indexedSeries: Array<{ date: string; basket_return: number }>): Array<{ date: string; value: number }> => {
    const dailyReturns = indexedSeries.map((point, index, all) => {
        if (index === 0) {
            return { date: point.date, value: 0 }
        }
        const previous = all[index - 1].basket_return
        const value = previous === 0 ? 0 : point.basket_return / previous - 1
        return { date: point.date, value }
    })

    const window = 20
    return dailyReturns.map((point, index, all) => {
        if (index < window) {
            return { date: point.date, value: 0 }
        }

        const sample = all.slice(index - window, index).map((item) => item.value)
        const mean = sample.reduce((sum, value) => sum + value, 0) / sample.length
        const variance = sample.reduce((sum, value) => sum + (value - mean) ** 2, 0) / sample.length
        return { date: point.date, value: Math.sqrt(variance) * Math.sqrt(252) }
    })
}

export function PerformanceTab({ config }: PerformanceTabProps): JSX.Element {
    const queryClient = useQueryClient()
    const query = usePerformanceQuery(config)
    const factorsQuery = useFactorsQuery(config, [], 63)

    if (query.isLoading) {
        return (
            <div className="space-y-3">
                <LoadingSkeleton className="h-24" />
                <LoadingSkeleton className="h-80" />
                <LoadingSkeleton className="h-64" />
            </div>
        )
    }

    if (query.error) {
        throw query.error
    }

    if (!query.data) {
        return <LoadingSkeleton className="h-80" />
    }

    const { series, metrics } = query.data
    const regimeIndex = { growth: 0, inflation: 1, 'risk-off': 2 }
    const regimeByDate = new Map((factorsQuery.data?.exposures ?? []).map((item) => [item.date, item.regime]))
    const regimeSeries = series
        .map((point) => {
            const regime = regimeByDate.get(point.date)
            if (!regime) {
                return null
            }
            return {
                date: point.date,
                basket_return: point.basket_return,
                regime_index: regimeIndex[regime as keyof typeof regimeIndex],
            }
        })
        .filter((item): item is { date: string; basket_return: number; regime_index: number } => item !== null)
    const volSeries = rollingVol(series)
    const xTickFormatter = buildXAxisFormatter(config.start_date, config.end_date)
    const xInterval = diffDays(config.start_date, config.end_date) > 90 ? 6 : 0

    const cards = [
        { label: 'Ann Vol', value: fmtPct(metrics.annVol), tooltip: 'Annualized volatility of basket returns.' },
        { label: 'Sharpe', value: fmtMultiple(metrics.sharpe), tooltip: 'Risk-adjusted return per unit of volatility.' },
        { label: 'Max Drawdown', value: fmtPct(metrics.maxDrawdown), tooltip: 'Largest peak-to-trough decline.' },
        { label: 'Calmar', value: fmtMultiple(metrics.calmar), tooltip: 'Annual return divided by max drawdown.' },
        { label: 'Sortino', value: fmtMultiple(metrics.sortino), tooltip: 'Risk-adjusted return using downside volatility.' },
        { label: 'Beta', value: fmtMultiple(metrics.beta), tooltip: 'Sensitivity versus benchmark return changes.' },
        { label: 'Net Exposure', value: fmtMultiple(metrics.netExposure), tooltip: 'Signed sum of basket weights.' },
        { label: 'Gross Exposure', value: fmtMultiple(metrics.grossExposure), tooltip: 'Sum of absolute basket weights.' },
        { label: 'Total Return', value: fmtPct(metrics.totalReturn), tooltip: 'Cumulative basket return over selected dates.' },
        { label: 'Vs Benchmark', value: fmtPct(metrics.vsbenchmark), tooltip: 'Basket total return minus benchmark return.' },
    ]

    const exportCsv = (): void => {
        const cached = queryClient.getQueryData<PerformanceResponse>(['analytics', 'performance', config])
        if (!cached) {
            return
        }

        const header = 'date,basket_return,benchmark_return,drawdown'
        const rows = cached.series.map(
            (item) => `${item.date},${item.basket_return},${item.benchmark_return},${item.drawdown}`,
        )
        const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv;charset=utf-8;' })
        const link = document.createElement('a')
        const url = URL.createObjectURL(blob)
        link.href = url
        link.setAttribute('download', `equity-curve-${config.start_date}-to-${config.end_date}.csv`)
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
    }

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
                {cards.map((card) => (
                    <StatCard key={card.label} label={card.label} value={card.value} tooltip={card.tooltip} />
                ))}
            </div>

            <div>
                <button
                    type="button"
                    onClick={exportCsv}
                    className="rounded-sm border border-[#1a1a1a] bg-[#050505] px-3 py-1 text-sm text-[#d7d7d7] transition-colors duration-150 hover:bg-[#0d0d0d]"
                >
                    Export Equity Curve CSV
                </button>
            </div>

            <ErrorBoundary>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                    <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Equity Curve & Drawdown</h3>
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={series}>
                                <CartesianGrid stroke="#1a1a1a" strokeDasharray="4 4" />
                                <XAxis
                                    dataKey="date"
                                    tickFormatter={xTickFormatter}
                                    interval={xInterval}
                                    stroke="#8a8a8a"
                                />
                                <YAxis stroke="#8a8a8a" />
                                <Tooltip labelFormatter={formatTooltipLabel} />
                                <Line type="monotone" dataKey="basket_return" stroke="#00ff9d" dot={false} />
                                <Line type="monotone" dataKey="benchmark_return" stroke="#3d7eff" dot={false} />
                                <Line type="monotone" dataKey="drawdown" stroke="#ff3d5a" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>

            <ErrorBoundary>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                    <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Rolling Volatility (20D)</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={volSeries}>
                                <CartesianGrid stroke="#1a1a1a" strokeDasharray="4 4" />
                                <XAxis
                                    dataKey="date"
                                    tickFormatter={xTickFormatter}
                                    interval={xInterval}
                                    stroke="#8a8a8a"
                                />
                                <YAxis stroke="#8a8a8a" tickFormatter={fmtPct} />
                                <Tooltip
                                    formatter={(value) => fmtPct(value as number)}
                                    labelFormatter={formatTooltipLabel}
                                />
                                <Line type="monotone" dataKey="value" stroke="#f5a623" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>

            {regimeSeries.length > 0 ? (
                <ErrorBoundary>
                    <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                        <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Regime Overlay</h3>
                        <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={regimeSeries}>
                                    <CartesianGrid stroke="#1a1a1a" strokeDasharray="4 4" />
                                    <XAxis
                                        dataKey="date"
                                        tickFormatter={xTickFormatter}
                                        interval={xInterval}
                                        stroke="#8a8a8a"
                                    />
                                    <YAxis yAxisId="left" stroke="#8a8a8a" />
                                    <YAxis yAxisId="right" orientation="right" stroke="#8a8a8a" domain={[0, 2]} ticks={[0, 1, 2]} />
                                    <Tooltip labelFormatter={formatTooltipLabel} />
                                    <Line yAxisId="left" type="monotone" dataKey="basket_return" stroke="#00ff9d" dot={false} />
                                    <Line yAxisId="right" type="stepAfter" dataKey="regime_index" stroke="#f5a623" dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </ErrorBoundary>
            ) : null}
        </div>
    )
}
