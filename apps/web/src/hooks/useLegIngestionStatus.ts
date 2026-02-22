import { useQueries } from '@tanstack/react-query'

import { api } from '../lib/api'
import type { DraftLeg } from '../stores/basketStore'

export const useLegIngestionStatus = (legs: DraftLeg[]) => {
    const ingestingLegs = legs.filter((leg) => leg.instrument.ingesting === true)

    const queries = useQueries({
        queries: ingestingLegs.map((leg) => ({
            queryKey: ['instrument-ingestion-status', leg.instrument_id],
            queryFn: () => api.getInstrumentIngestionStatus(leg.instrument_id),
            refetchInterval: (query: { state: { data?: { status?: string } } }) => {
                const status = query.state.data?.status
                return status === 'complete' || status === 'failed' ? false : 3_000
            },
        })),
    })

    const statusByInstrumentId = new Map<string, 'complete' | 'ingesting' | 'failed'>()
    ingestingLegs.forEach((leg, index) => {
        statusByInstrumentId.set(leg.instrument_id, queries[index].data?.status ?? 'ingesting')
    })

    return {
        statusByInstrumentId,
        hasPolling: ingestingLegs.length > 0,
    }
}
