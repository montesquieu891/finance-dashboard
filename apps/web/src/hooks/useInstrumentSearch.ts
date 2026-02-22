import { useQuery } from '@tanstack/react-query'

import { api } from '../lib/api'

export const useInstrumentSearch = (query: string) =>
    useQuery({
        queryKey: ['instruments', query, 'auto'],
        queryFn: () => api.searchInstruments(query, 'auto'),
        enabled: query.trim().length >= 2,
        staleTime: 60_000,
    })
