interface StatCardProps {
    label: string
    value: string
}

export function StatCard({ label, value }: StatCardProps): JSX.Element {
    return (
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-3">
            <p className="text-xs text-slate-400">{label}</p>
            <p className="mt-1 text-lg font-semibold text-slate-100">{value}</p>
        </div>
    )
}
