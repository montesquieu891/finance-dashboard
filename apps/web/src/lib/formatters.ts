import { format } from 'date-fns'

export const fmtPct = (value: number): string => `${(value * 100).toFixed(2)}%`

export const fmtNumber = (value: number): string =>
    new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)

export const fmtDate = (value: string): string => format(new Date(value), 'yyyy-MM-dd')

export const fmtBps = (value: number): string => `${value.toFixed(1)} bps`

export const fmtCurrency = (value: number): string =>
    new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 2,
    }).format(value)

export const fmtMultiple = (value: number): string => `${value.toFixed(2)}x`

export const diffDays = (startDate: string, endDate: string): number => {
    const start = new Date(startDate)
    const end = new Date(endDate)
    const millis = Math.max(0, end.getTime() - start.getTime())
    return Math.ceil(millis / (1000 * 60 * 60 * 24))
}

export const buildXAxisFormatter = (startDate: string, endDate: string): ((value: string) => string) => {
    const days = diffDays(startDate, endDate)
    if (days > 90) {
        return (value: string): string => format(new Date(value), "MMM dd")
    }
    return (value: string): string => format(new Date(value), "MM-dd")
}
