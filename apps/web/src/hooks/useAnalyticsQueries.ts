import { useQuery } from '@tanstack/react-query'

import { api } from '../lib/api'
import type { BasketConfig } from '../types/domain'

export const usePerformanceQuery = (config: BasketConfig | null) =>
    useQuery({
        queryKey: ['analytics', 'performance', config],
        queryFn: () => {
            if (!config) {
                throw new Error('Basket config is missing')
            }
            return api.getPerformance(config)
        },
        enabled: config !== null,
    })

export const useWeightsQuery = (config: BasketConfig | null) =>
    useQuery({
        queryKey: ['analytics', 'weights', config],
        queryFn: () => {
            if (!config) {
                throw new Error('Basket config is missing')
            }
            return api.getWeights(config)
        },
        enabled: config !== null,
    })

export const useRiskQuery = (config: BasketConfig | null) =>
    useQuery({
        queryKey: ['analytics', 'risk', config],
        queryFn: () => {
            if (!config) {
                throw new Error('Basket config is missing')
            }
            return api.getRisk(config)
        },
        enabled: config !== null,
    })

export const useCorrelationQuery = (config: BasketConfig | null) =>
    useQuery({
        queryKey: ['analytics', 'correlation', config],
        queryFn: () => {
            if (!config) {
                throw new Error('Basket config is missing')
            }
            return api.getCorrelation(config)
        },
        enabled: config !== null,
    })

export const useHealthQuery = () =>
    useQuery({
        queryKey: ['health'],
        queryFn: () => api.getHealth(),
        refetchInterval: 60_000,
    })

export const useBasketsQuery = () =>
    useQuery({
        queryKey: ['baskets'],
        queryFn: () => api.listBaskets(),
        staleTime: 30_000,
    })

export const useFactorDefinitionsQuery = () =>
    useQuery({
        queryKey: ['analytics', 'factors', 'definitions'],
        queryFn: () => api.listFactorDefinitions(),
        staleTime: 300_000,
    })

export const useFactorsQuery = (
    config: BasketConfig | null,
    factorCodes: string[],
    rollingWindow = 63,
) =>
    useQuery({
        queryKey: ['analytics', 'factors', config, factorCodes, rollingWindow],
        queryFn: () => {
            if (!config) {
                throw new Error('Basket config is missing')
            }
            return api.getFactors({ config, factor_codes: factorCodes, rolling_window: rollingWindow })
        },
        enabled: config !== null,
    })
