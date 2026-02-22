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
import { buildXAxisFormatter, diffDays, fmtDate, fmtMultiple, fmtPct } from '../../lib/formatters'
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
    const xTickFormatter = buildXAxisFormatter(config.start_date, config.end_date)
    const xInterval = diffDays(config.start_date, config.end_date) > 90 ? 6 : 0
    const rows = [
        { label: 'Ann Vol', value: fmtPct(metrics.annVol) },
        { label: 'Sharpe', value: fmtMultiple(metrics.sharpe) },
        { label: 'Max Drawdown', value: fmtPct(metrics.maxDrawdown) },
        { label: 'Calmar', value: fmtMultiple(metrics.calmar) },
        { label: 'Sortino', value: fmtMultiple(metrics.sortino) },
        { label: 'Beta', value: fmtMultiple(metrics.beta) },
        { label: 'Net Exposure', value: fmtMultiple(metrics.netExposure) },
        { label: 'Gross Exposure', value: fmtMultiple(metrics.grossExposure) },
        { label: 'Funding Drag', value: fmtMultiple(metrics.fundingDrag) },
        { label: 'Total Return', value: fmtPct(metrics.totalReturn) },
        { label: 'Vs Benchmark', value: fmtPct(metrics.vsbenchmark) },
    ]

    const volSeries = performanceQuery.data.series.map((point) => ({
        date: point.date,
        vol: point.drawdown,
    }))

    return (
        <div className="space-y-4">
            <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                <h3 className="ui-label mb-2 font-semibold text-[#d7d7d7]">Risk Metrics</h3>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    {rows.map((row) => (
                        <div key={row.label} className="flex items-center justify-between rounded border border-[#1a1a1a] bg-[#050505] px-3 py-2 text-sm">
                            <span className="ui-label">{row.label}</span>
                            <span className="font-medium text-[#d7d7d7] tabular-nums">{row.value}</span>
                        </div>
                    ))}
                </div>
            </div>

            <ErrorBoundary>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                    <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Rolling Volatility Proxy</h3>
                    <div className="h-72">
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
                                    labelFormatter={formatTooltipLabel}
                                    formatter={(value) => fmtPct(value as number)}
                                />
                                <Line dataKey="vol" stroke="#f5a623" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>
        </div>
    )
}
