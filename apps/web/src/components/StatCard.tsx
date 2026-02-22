interface StatCardProps {
    label: string
    value: string
    tooltip: string
}

export function StatCard({ label, value, tooltip }: StatCardProps): JSX.Element {
    return (
        <div className="rounded border border-[#1a1a1a] bg-[#080808] p-3" title={tooltip}>
            <p className="ui-label">{label} ⓘ</p>
            <p className="mt-1 text-lg font-semibold text-[#d7d7d7] tabular-nums">{value}</p>
        </div>
    )
}
