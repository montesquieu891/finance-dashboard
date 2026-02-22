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
import { usePerformanceQuery, useRiskQuery } from '../../hooks/useAnalyticsQueries'
import { fmtDate, fmtNumber, fmtPct } from '../../lib/formatters'
import type { BasketConfig } from '../../types/domain'

interface RiskTabProps {
    config: BasketConfig
}

const formatTooltipLabel = (label: unknown): string =>
    typeof label === 'string' ? fmtDate(label) : String(label)

export function RiskTab({ config }: RiskTabProps): JSX.Element {
    const riskQuery = useRiskQuery(config)
    const performanceQuery = usePerformanceQuery(config)

    if (riskQuery.isLoading || performanceQuery.isLoading) {
        return (
            <div className="space-y-3">
                <LoadingSkeleton className="h-56" />
                <LoadingSkeleton className="h-72" />
            </div>
        )
    }

    if (riskQuery.error) {
        throw riskQuery.error
    }

    if (performanceQuery.error) {
        throw performanceQuery.error
    }

    if (!riskQuery.data || !performanceQuery.data) {
        return <LoadingSkeleton className="h-72" />
    }

    const metrics = riskQuery.data.metrics
    const rows = [
        { label: 'Ann Vol', value: fmtPct(metrics.annVol) },
        { label: 'Sharpe', value: fmtNumber(metrics.sharpe) },
        { label: 'Max Drawdown', value: fmtPct(metrics.maxDrawdown) },
        { label: 'Calmar', value: fmtNumber(metrics.calmar) },
        { label: 'Sortino', value: fmtNumber(metrics.sortino) },
        { label: 'Beta', value: fmtNumber(metrics.beta) },
        { label: 'Net Exposure', value: fmtNumber(metrics.netExposure) },
        { label: 'Gross Exposure', value: fmtNumber(metrics.grossExposure) },
        { label: 'Funding Drag', value: fmtNumber(metrics.fundingDrag) },
        { label: 'Total Return', value: fmtPct(metrics.totalReturn) },
        { label: 'Vs Benchmark', value: fmtPct(metrics.vsbenchmark) },
    ]

    const volSeries = performanceQuery.data.series.map((point) => ({
        date: point.date,
        vol: point.drawdown,
    }))

    return (
        <div className="space-y-4">
            <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
                <h3 className="mb-2 text-sm font-semibold text-slate-200">Risk Metrics</h3>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    {rows.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded bg-slate-950 px-3 py-2 text-sm">
                            <span className="text-slate-400">{row.label}</span>
                            <span className="font-medium text-slate-100">{row.value}</span>
                        </div>
                    ))}
                </div>
            </div>

            <ErrorBoundary>
                <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-slate-200">Rolling Volatility Proxy</h3>
                    <div className="h-72">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={volSeries}>
                                <CartesianGrid stroke="#334155" strokeDasharray="4 4" />
                                <XAxis dataKey="date" tickFormatter={fmtDate} stroke="#94a3b8" />
                                <YAxis stroke="#94a3b8" tickFormatter={fmtPct} />
                                <Tooltip
                                    labelFormatter={formatTooltipLabel}
                                    formatter={(value) => fmtPct(value as number)}
                                />
                                <Line dataKey="vol" stroke="#f59e0b" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>
        </div>
    )
}
