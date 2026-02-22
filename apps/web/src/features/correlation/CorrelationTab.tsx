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
    return clamped >= 0 ? `rgba(0,255,157,${alpha})` : `rgba(255,61,90,${alpha})`
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
            <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Correlation Matrix</h3>
                <div className="overflow-x-auto">
                    <table className="min-w-full text-xs">
                        <thead>
                            <tr>
                                <th className="ui-label px-2 py-2 text-left">Symbol</th>
                                {symbols.map((symbol) => (
                                    <th key={symbol} className="ui-label px-2 py-2 text-right">
                                        {symbol}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {symbols.map((rowSymbol, rowIndex) => (
                                <tr key={rowSymbol} className="border-b border-[#1a1a1a]">
                                    <td className="px-2 py-2 font-medium text-[#d7d7d7]">{rowSymbol}</td>
                                    {matrix[rowIndex].map((value, columnIndex) => (
                                        <td
                                            key={`${rowSymbol}-${symbols[columnIndex]}`}
                                            className="px-2 py-2 text-right text-[#d7d7d7] tabular-nums"
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
