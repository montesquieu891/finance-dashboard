import { ErrorBoundary } from '../../components/ErrorBoundary'
import { LoadingSkeleton } from '../../components/LoadingSkeleton'
import { useCorrelationQuery } from '../../hooks/useAnalyticsQueries'
import { fmtNumber } from '../../lib/formatters'
import type { BasketConfig } from '../../types/domain'

interface CorrelationTabProps {
    config: BasketConfig
}

const corrColor = (value: number): string => {
    const clamped = Math.max(-1, Math.min(1, value))
    const alpha = Math.abs(clamped)
    return clamped >= 0 ? `rgba(16,185,129,${alpha})` : `rgba(239,68,68,${alpha})`
}

export function CorrelationTab({ config }: CorrelationTabProps): JSX.Element {
    const query = useCorrelationQuery(config)

    if (query.isLoading) {
        return <LoadingSkeleton className="h-80" />
    }

    if (query.error) {
        throw query.error
    }

    if (!query.data) {
        return <LoadingSkeleton className="h-80" />
    }

    const symbols = query.data.symbols
    const matrix = query.data.matrix

    return (
        <ErrorBoundary>
            <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
                <h3 className="mb-3 text-sm font-semibold text-slate-200">Correlation Matrix</h3>
                <div className="overflow-x-auto">
                    <table className="min-w-full text-xs">
                        <thead>
                            <tr>
                                <th className="px-2 py-2 text-left text-slate-400">Symbol</th>
                                {symbols.map((symbol) => (
                                    <th key={symbol} className="px-2 py-2 text-right text-slate-400">
                                        {symbol}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {symbols.map((rowSymbol, rowIndex) => (
                                <tr key={rowSymbol}>
                                    <td className="px-2 py-2 font-medium text-slate-200">{rowSymbol}</td>
                                    {matrix[rowIndex].map((value, columnIndex) => (
                                        <td
                                            key={`${rowSymbol}-${symbols[columnIndex]}`}
                                            className="px-2 py-2 text-right text-slate-100"
                                            style={{ backgroundColor: corrColor(value) }}
                                        >
                                            {fmtNumber(value)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </ErrorBoundary>
    )
}
