import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ErrorBoundary } from '../../components/ErrorBoundary'
import { LoadingSkeleton } from '../../components/LoadingSkeleton'
import { useWeightsQuery } from '../../hooks/useAnalyticsQueries'
import { fmtMultiple } from '../../lib/formatters'
import type { BasketConfig } from '../../types/domain'

interface WeightsTabProps {
    config: BasketConfig
}

const heatColor = (value: number): string => {
    const clamped = Math.min(1, Math.max(-1, value))
    const alpha = Math.abs(clamped)
    if (clamped >= 0) {
        return `rgba(0,255,157,${alpha})`
    }
    return `rgba(255,61,90,${alpha})`
}

export function WeightsTab({ config }: WeightsTabProps): JSX.Element {
    const query = useWeightsQuery(config)

    if (query.isLoading) {
        return (
            <div className="space-y-3">
                <LoadingSkeleton className="h-64" />
                <LoadingSkeleton className="h-64" />
            </div>
        )
    }

    if (query.error) {
        throw query.error
    }

    if (!query.data) {
        return <LoadingSkeleton className="h-64" />
    }

    const snapshots = query.data.weights
    const symbols = (() => {
        const set = new Set<string>()
        snapshots.forEach((snapshot) => {
            Object.keys(snapshot.weights).forEach((symbol) => set.add(symbol))
        })
        return Array.from(set)
    })()

    const selectedMethod = snapshots.find((item) => item.method === config.weight_method) ?? snapshots[0]
    const chartData = Object.entries(selectedMethod.weights).map(([symbol, weight]) => ({ symbol, weight }))

    return (
        <div className="space-y-4">
            <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Weights Table (All Methods)</h3>
                <div className="overflow-x-auto">
                    <table className="min-w-full text-xs text-[#d7d7d7]">
                        <thead>
                            <tr className="border-b border-[#1a1a1a]">
                                <th className="ui-label px-2 py-2 text-left">Method</th>
                                {symbols.map((symbol) => (
                                    <th key={symbol} className="ui-label px-2 py-2 text-right">
                                        {symbol}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {snapshots.map((snapshot) => (
                                <tr key={snapshot.method} className="border-b border-[#1a1a1a] hover:bg-[#0d0d0d]">
                                    <td className="px-2 py-2 font-medium uppercase tracking-[0.12em]">{snapshot.method}</td>
                                    {symbols.map((symbol) => (
                                        <td key={symbol} className="px-2 py-2 text-right tabular-nums">
                                            {fmtMultiple(snapshot.weights[symbol] ?? 0)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <ErrorBoundary>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                    <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Bar Chart ({selectedMethod.method})</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData}>
                                <CartesianGrid stroke="#1a1a1a" strokeDasharray="4 4" />
                                <XAxis dataKey="symbol" stroke="#8a8a8a" />
                                <YAxis stroke="#8a8a8a" />
                                <Tooltip formatter={(value) => fmtMultiple(value as number)} />
                                <Bar dataKey="weight" fill="#00ff9d" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>

            <ErrorBoundary>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                    <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Weights Heatmap</h3>
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-xs text-[#d7d7d7]">
                            <thead>
                                <tr>
                                    <th className="ui-label px-2 py-2 text-left">Method</th>
                                    {symbols.map((symbol) => (
                                        <th key={symbol} className="ui-label px-2 py-2 text-right">
                                            {symbol}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {snapshots.map((snapshot) => (
                                    <tr key={snapshot.method} className="border-b border-[#1a1a1a]">
                                        <td className="px-2 py-2 font-medium uppercase tracking-[0.12em]">{snapshot.method}</td>
                                        {symbols.map((symbol) => {
                                            const value = snapshot.weights[symbol] ?? 0
                                            return (
                                                <td
                                                    key={symbol}
                                                    className="px-2 py-2 text-right tabular-nums"
                                                    style={{ backgroundColor: heatColor(value) }}
                                                >
                                                    {fmtMultiple(value)}
                                                </td>
                                            )
                                        })}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </ErrorBoundary>
        </div>
    )
}
