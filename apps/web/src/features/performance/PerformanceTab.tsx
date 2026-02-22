import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'

import { ErrorBoundary } from '../../components/ErrorBoundary'
import { LoadingSkeleton } from '../../components/LoadingSkeleton'
import { StatCard } from '../../components/StatCard'
import { usePerformanceQuery } from '../../hooks/useAnalyticsQueries'
import { fmtDate, fmtNumber, fmtPct } from '../../lib/formatters'
import type { BasketConfig } from '../../types/domain'

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
    const query = usePerformanceQuery(config)

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
    const volSeries = rollingVol(series)

    const cards = [
        { label: 'Ann Vol', value: fmtPct(metrics.annVol) },
        { label: 'Sharpe', value: fmtNumber(metrics.sharpe) },
        { label: 'Max Drawdown', value: fmtPct(metrics.maxDrawdown) },
        { label: 'Calmar', value: fmtNumber(metrics.calmar) },
        { label: 'Sortino', value: fmtNumber(metrics.sortino) },
        { label: 'Beta', value: fmtNumber(metrics.beta) },
        { label: 'Net Exposure', value: fmtNumber(metrics.netExposure) },
        { label: 'Gross Exposure', value: fmtNumber(metrics.grossExposure) },
        { label: 'Total Return', value: fmtPct(metrics.totalReturn) },
        { label: 'Vs Benchmark', value: fmtPct(metrics.vsbenchmark) },
    ]

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
                {cards.map((card) => (
                    <StatCard key={card.label} label={card.label} value={card.value} />
                ))}
            </div>

            <ErrorBoundary>
                <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-slate-200">Equity Curve & Drawdown</h3>
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={series}>
                                <CartesianGrid stroke="#334155" strokeDasharray="4 4" />
                                <XAxis dataKey="date" tickFormatter={fmtDate} stroke="#94a3b8" />
                                <YAxis stroke="#94a3b8" />
                                <Tooltip labelFormatter={formatTooltipLabel} />
                                <Line type="monotone" dataKey="basket_return" stroke="#38bdf8" dot={false} />
                                <Line type="monotone" dataKey="benchmark_return" stroke="#22c55e" dot={false} />
                                <Line type="monotone" dataKey="drawdown" stroke="#f97316" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>

            <ErrorBoundary>
                <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-slate-200">Rolling Volatility (20D)</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={volSeries}>
                                <CartesianGrid stroke="#334155" strokeDasharray="4 4" />
                                <XAxis dataKey="date" tickFormatter={fmtDate} stroke="#94a3b8" />
                                <YAxis stroke="#94a3b8" tickFormatter={fmtPct} />
                                <Tooltip
                                    formatter={(value) => fmtPct(value as number)}
                                    labelFormatter={formatTooltipLabel}
                                />
                                <Line type="monotone" dataKey="value" stroke="#a78bfa" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>
        </div>
    )
}
