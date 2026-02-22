import { format } from 'date-fns'

export const fmtPct = (value: number): string => `${(value * 100).toFixed(2)}%`

export const fmtNumber = (value: number): string =>
    new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)

export const fmtDate = (value: string): string => format(new Date(value), 'yyyy-MM-dd')

export const fmtBps = (value: number): string => `${value.toFixed(1)} bps`
