import { useQuery } from '@tanstack/react-query'

import { api } from '../lib/api'

export const useInstrumentSearch = (query: string) =>
    useQuery({
        queryKey: ['instruments', query],
        queryFn: () => api.searchInstruments(query),
        enabled: query.trim().length >= 2,
        staleTime: 60_000,
    })
