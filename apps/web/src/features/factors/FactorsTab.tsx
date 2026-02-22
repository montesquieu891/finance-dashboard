import { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ErrorBoundary } from '../../components/ErrorBoundary'
import { LoadingSkeleton } from '../../components/LoadingSkeleton'
import { useFactorDefinitionsQuery, useFactorsQuery } from '../../hooks/useAnalyticsQueries'
import { fmtDate, fmtPct } from '../../lib/formatters'
import type { BasketConfig } from '../../types/domain'

interface FactorsTabProps {
    config: BasketConfig
}

const regimeColor = (regime: string): string => {
    if (regime === 'inflation') return '#f5a623'
    if (regime === 'risk-off') return '#ff3d5a'
    return '#00ff9d'
}

const corrColor = (value: number): string => {
    const clamped = Math.max(-1, Math.min(1, value))
    const alpha = Math.abs(clamped)
    return clamped >= 0 ? `rgba(0,255,157,${alpha})` : `rgba(255,61,90,${alpha})`
}

export function FactorsTab({ config }: FactorsTabProps): JSX.Element {
    const definitionsQuery = useFactorDefinitionsQuery()
    const [selectedFactors, setSelectedFactors] = useState<string[]>([])

    const defaultCodes = useMemo(
        () => definitionsQuery.data?.map((item) => item.code) ?? [],
        [definitionsQuery.data],
    )
    const activeCodes = selectedFactors.length > 0 ? selectedFactors : defaultCodes

    const factorsQuery = useFactorsQuery(config, activeCodes)

    if (definitionsQuery.isLoading || factorsQuery.isLoading) {
        return (
            <div className="space-y-3">
                <LoadingSkeleton className="h-24" />
                <LoadingSkeleton className="h-72" />
                <LoadingSkeleton className="h-64" />
            </div>
        )
    }

    if (definitionsQuery.error) {
        throw definitionsQuery.error
    }

    if (factorsQuery.error) {
        throw factorsQuery.error
    }

    if (!definitionsQuery.data || !factorsQuery.data) {
        return <LoadingSkeleton className="h-72" />
    }

    const definitions = definitionsQuery.data
    const response = factorsQuery.data
    const exposureSeries = response.exposures.map((point) => ({
        date: point.date,
        regime: point.regime,
        ...point.exposures,
    }))
    const factorCodes = response.factor_correlation.factors

    const onToggleFactor = (code: string): void => {
        setSelectedFactors((prev) => {
            if (prev.includes(code)) {
                return prev.filter((item) => item !== code)
            }
            return [...prev, code]
        })
    }

    return (
        <div className="space-y-4">
            <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Factor Selector</h3>
                <div className="flex flex-wrap gap-2">
                    {definitions.map((factor) => {
                        const selected = activeCodes.includes(factor.code)
                        return (
                            <button
                                key={factor.code}
                                type="button"
                                onClick={() => onToggleFactor(factor.code)}
                                className={`rounded-sm border px-2 py-1 text-xs transition-colors ${selected
                                    ? 'border-[#00ff9d] text-[#00ff9d]'
                                    : 'border-[#1a1a1a] text-[#8a8a8a] hover:text-[#d7d7d7]'
                                    }`}
                            >
                                {factor.code} ({factor.proxy_symbol})
                            </button>
                        )
                    })}
                </div>
            </div>

            <ErrorBoundary>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                    <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Factor Exposure Time Series</h3>
                    <div className="h-72">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={exposureSeries}>
                                <CartesianGrid stroke="#1a1a1a" strokeDasharray="4 4" />
                                <XAxis dataKey="date" tickFormatter={fmtDate} stroke="#8a8a8a" />
                                <YAxis stroke="#8a8a8a" />
                                <Tooltip labelFormatter={(value) => fmtDate(String(value))} />
                                {factorCodes.map((code, index) => {
                                    const colors = ['#00ff9d', '#3d7eff', '#f5a623', '#ff3d5a', '#8a8a8a', '#d7d7d7']
                                    return <Line key={code} dataKey={code} stroke={colors[index % colors.length]} dot={false} />
                                })}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>

            <ErrorBoundary>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                    <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">PnL Attribution</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={response.attribution}>
                                <CartesianGrid stroke="#1a1a1a" strokeDasharray="4 4" />
                                <XAxis dataKey="factor" stroke="#8a8a8a" />
                                <YAxis stroke="#8a8a8a" tickFormatter={fmtPct} />
                                <Tooltip formatter={(value) => fmtPct(Number(value))} />
                                <Bar dataKey="contribution" fill="#00ff9d" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </ErrorBoundary>

            <ErrorBoundary>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                    <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Regime Map</h3>
                    <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                        {response.exposures.slice(-8).map((item) => (
                            <div key={item.date} className="rounded border border-[#1a1a1a] bg-[#050505] px-3 py-2 text-xs">
                                <div className="ui-label">{fmtDate(item.date)}</div>
                                <div style={{ color: regimeColor(item.regime) }} className="mt-1 font-semibold uppercase tracking-[0.08em]">
                                    {item.regime}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </ErrorBoundary>

            <ErrorBoundary>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-4">
                    <h3 className="ui-label mb-3 font-semibold text-[#d7d7d7]">Factor Correlation</h3>
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-xs text-[#d7d7d7]">
                            <thead>
                                <tr>
                                    <th className="ui-label px-2 py-2 text-left">Factor</th>
                                    {factorCodes.map((factor) => (
                                        <th key={factor} className="ui-label px-2 py-2 text-right">
                                            {factor}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {factorCodes.map((rowFactor, rowIndex) => (
                                    <tr key={rowFactor} className="border-b border-[#1a1a1a]">
                                        <td className="px-2 py-2 font-medium">{rowFactor}</td>
                                        {response.factor_correlation.matrix[rowIndex].map((value, colIndex) => (
                                            <td
                                                key={`${rowFactor}-${factorCodes[colIndex]}`}
                                                className="px-2 py-2 text-right tabular-nums"
                                                style={{ backgroundColor: corrColor(value) }}
                                            >
                                                {value.toFixed(2)}
                                            </td>
                                        ))}
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
