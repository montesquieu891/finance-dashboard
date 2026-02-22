import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ErrorBoundary } from '../../components/ErrorBoundary'
import { LoadingSkeleton } from '../../components/LoadingSkeleton'
import { useWeightsQuery } from '../../hooks/useAnalyticsQueries'
import { fmtNumber } from '../../lib/formatters'
import type { BasketConfig } from '../../types/domain'

interface WeightsTabProps {
    config: BasketConfig
}

const heatColor = (value: number): string => {
    const clamped = Math.min(1, Math.max(-1, value))
    const alpha = Math.abs(clamped)
    if (clamped >= 0) {
        return `rgba(34,197,94,${alpha})`
    }
    return `rgba(239,68,68,${alpha})`
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
            <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
                <h3 className="mb-3 text-sm font-semibold text-slate-200">Weights Table (All Methods)</h3>
                <div className="overflow-x-auto">
                    <table className="min-w-full text-xs text-slate-200">
                        <thead>
                            <tr className="border-b border-slate-700 text-slate-400">
                                <th className="px-2 py-2 text-left">Method</th>
                                {symbols.map((symbol) => (
                                    <th key={symbol} className="px-2 py-2 text-right">
                                        {symbol}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {snapshots.map((snapshot) => (
                                <tr key={snapshot.method} className="border-b border-slate-800">
                                    <td className="px-2 py-2 font-medium">{snapshot.method}</td>
                                    {symbols.map((symbol) => (
                                        <td key={symbol} className="px-2 py-2 text-right">
                                            {fmtNumber(snapshot.weights[symbol] ?? 0)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <ErrorBoundary>
                <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-slate-200">Bar Chart ({selectedMethod.method})</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData}>
                                <CartesianGrid stroke="#334155" strokeDasharray="4 4" />
                                <XAxis dataKey="symbol" stroke="#94a3b8" />
                                <YAxis stroke="#94a3b8" />
                                <Tooltip formatter={(value) => fmtNumber(value as number)} />
                                <Bar dataKey="weight" fill="#38bdf8" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>

            <ErrorBoundary>
                <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-slate-200">Weights Heatmap</h3>
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-xs text-slate-100">
                            <thead>
                                <tr>
                                    <th className="px-2 py-2 text-left">Method</th>
                                    {symbols.map((symbol) => (
                                        <th key={symbol} className="px-2 py-2 text-right">
                                            {symbol}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {snapshots.map((snapshot) => (
                                    <tr key={snapshot.method}>
                                        <td className="px-2 py-2 font-medium">{snapshot.method}</td>
                                        {symbols.map((symbol) => {
                                            const value = snapshot.weights[symbol] ?? 0
                                            return (
                                                <td
                                                    key={symbol}
                                                    className="px-2 py-2 text-right"
                                                    style={{ backgroundColor: heatColor(value) }}
                                                >
                                                    {fmtNumber(value)}
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
