import { useQueries } from '@tanstack/react-query'

import { api } from '../lib/api'
import type { Instrument } from '../types/domain'

export interface InstrumentSnapshot {
    instrumentId: string
    lastPrice: number | null
    dailyReturn: number | null
}

const fromDate = (): string => {
    const value = new Date()
    value.setDate(value.getDate() - 14)
    return value.toISOString().slice(0, 10)
}

const toDate = (): string => new Date().toISOString().slice(0, 10)

export const useInstrumentSnapshots = (instruments: Instrument[]) => {
    const queries = useQueries({
        queries: instruments.map((instrument) => ({
            queryKey: ['instrument-prices', instrument.id],
            queryFn: () => api.getInstrumentPrices(instrument.id, fromDate(), toDate()),
            staleTime: 60_000,
        })),
    })

    const result = new Map<string, InstrumentSnapshot>()
    instruments.forEach((instrument, index) => {
        const data = queries[index].data ?? []
        const latest = data[data.length - 1]
        const previous = data[data.length - 2]

        const lastPrice = latest?.px_close ? Number(latest.px_close) : null
        const previousPrice = previous?.px_close ? Number(previous.px_close) : null
        const dailyReturn =
            lastPrice !== null && previousPrice !== null && previousPrice !== 0
                ? lastPrice / previousPrice - 1
                : null

        result.set(instrument.id, {
            instrumentId: instrument.id,
            lastPrice,
            dailyReturn,
        })
    })

    return {
        snapshots: result,
        isLoading: queries.some((item) => item.isLoading),
    }
}
