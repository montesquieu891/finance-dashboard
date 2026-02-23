import { useRef } from 'react'

import { LoadingSkeleton } from '../../components/LoadingSkeleton'
import { usePositionsQuery, useUploadPositions } from '../../hooks/useLiveMonitoring'
import { fmtCurrency, fmtPct } from '../../lib/formatters'

interface PositionsTabProps {
    basketId: string
}

export function PositionsTab({ basketId }: PositionsTabProps): JSX.Element {
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const positionsQuery = usePositionsQuery(basketId)
    const uploadMutation = useUploadPositions(basketId)

    if (positionsQuery.isLoading) {
        return <LoadingSkeleton className="h-80" />
    }

    if (positionsQuery.error) {
        throw positionsQuery.error
    }

    const data = positionsQuery.data
    if (!data) {
        return <LoadingSkeleton className="h-80" />
    }

    const grossNotional = Number(data.summary.gross_notional)
    const netNotional = Number(data.summary.net_notional)
    const dailyPnl = Number(data.summary.daily_pnl_total)

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-3">
                <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="rounded-sm border border-[#1a1a1a] bg-[#050505] px-3 py-1 text-sm text-[#d7d7d7] transition-colors duration-150 hover:bg-[#0d0d0d]"
                >
                    Upload Positions CSV
                </button>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,text/csv"
                    className="hidden"
                    onChange={(event) => {
                        const file = event.target.files?.[0]
                        if (!file) {
                            return
                        }
                        uploadMutation.mutate(file)
                        event.currentTarget.value = ''
                    }}
                />
                {uploadMutation.isPending ? <p className="text-xs text-[#f5a623]">Uploading…</p> : null}
                {uploadMutation.error ? <p className="text-xs text-[#ff3d5a]">{uploadMutation.error.message}</p> : null}
            </div>

            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-3">
                    <p className="ui-label">Gross Notional</p>
                    <p className="mt-1 text-sm">{fmtCurrency(grossNotional)}</p>
                </div>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-3">
                    <p className="ui-label">Net Notional</p>
                    <p className="mt-1 text-sm">{fmtCurrency(netNotional)}</p>
                </div>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-3">
                    <p className="ui-label">Drift (L1)</p>
                    <p className="mt-1 text-sm text-[#f5a623]">{fmtPct(data.summary.drift_l1)}</p>
                </div>
                <div className="rounded border border-[#1a1a1a] bg-[#080808] p-3">
                    <p className="ui-label">Daily P&L</p>
                    <p className={`mt-1 text-sm ${dailyPnl >= 0 ? 'text-[#00ff9d]' : 'text-[#ff3d5a]'}`}>
                        {fmtCurrency(dailyPnl)}
                    </p>
                </div>
            </div>

            <div className="overflow-x-auto rounded border border-[#1a1a1a] bg-[#080808]">
                <table className="min-w-full text-xs">
                    <thead className="border-b border-[#1a1a1a] bg-[#050505] text-[#8a8a8a]">
                        <tr>
                            <th className="px-3 py-2 text-left font-medium">Symbol</th>
                            <th className="px-3 py-2 text-right font-medium">Qty</th>
                            <th className="px-3 py-2 text-right font-medium">Last</th>
                            <th className="px-3 py-2 text-right font-medium">Model W</th>
                            <th className="px-3 py-2 text-right font-medium">Actual W</th>
                            <th className="px-3 py-2 text-right font-medium">Drift (bps)</th>
                            <th className="px-3 py-2 text-right font-medium">P&L</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.rows.map((row) => {
                            const driftColor = row.drift_bps >= 0 ? 'text-[#f5a623]' : 'text-[#ff3d5a]'
                            const pnlValue = Number(row.daily_pnl ?? '0')
                            return (
                                <tr key={row.id} className="border-b border-[#1a1a1a] last:border-b-0">
                                    <td className="px-3 py-2">{row.symbol}</td>
                                    <td className="px-3 py-2 text-right">{Number(row.quantity).toFixed(2)}</td>
                                    <td className="px-3 py-2 text-right">
                                        {row.last_price ? fmtCurrency(Number(row.last_price)) : '--'}
                                    </td>
                                    <td className="px-3 py-2 text-right">{fmtPct(row.model_signed_weight)}</td>
                                    <td className="px-3 py-2 text-right">{fmtPct(row.actual_signed_weight)}</td>
                                    <td className={`px-3 py-2 text-right ${driftColor}`}>{row.drift_bps.toFixed(1)}</td>
                                    <td className={`px-3 py-2 text-right ${pnlValue >= 0 ? 'text-[#00ff9d]' : 'text-[#ff3d5a]'}`}>
                                        {fmtCurrency(pnlValue)}
                                    </td>
                                </tr>
                            )
                        })}
                        {data.rows.length === 0 ? (
                            <tr>
                                <td className="px-3 py-6 text-center text-[#8a8a8a]" colSpan={7}>
                                    Upload a CSV with symbol and quantity columns to track real positions.
                                </td>
                            </tr>
                        ) : null}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
