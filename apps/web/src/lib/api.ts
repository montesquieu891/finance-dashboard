import ky, { HTTPError } from 'ky'

import type {
    BasketConfig,
    BasketCreateRequest,
    BasketResponse,
    CorrelationResponse,
    PerformanceResponse,
    RiskResponse,
    SearchInstrumentsResponse,
    WeightsResponse,
} from '../types/domain'
import { apiBaseUrl } from './constants'

const client = ky.create({
    prefixUrl: apiBaseUrl,
    headers: {
        'X-API-Key': import.meta.env.VITE_API_KEY ?? 'dev-api-key',
    },
})

const toApiError = async (error: unknown): Promise<Error> => {
    if (error instanceof HTTPError) {
        try {
            const payload = (await error.response.json()) as { detail?: string; error?: string }
            const message = payload.detail ?? payload.error ?? `Request failed with ${error.response.status}`
            return new Error(message)
        } catch {
            return new Error(`Request failed with ${error.response.status}`)
        }
    }

    if (error instanceof Error) {
        return error
    }

    return new Error('Unknown API error')
}

export const api = {
    async searchInstruments(query: string): Promise<SearchInstrumentsResponse> {
        try {
            return await client
                .get('instruments/search', {
                    searchParams: {
                        q: query,
                        limit: '20',
                    },
                })
                .json<SearchInstrumentsResponse>()
        } catch (error) {
            throw await toApiError(error)
        }
    },
    async createBasket(payload: BasketCreateRequest): Promise<BasketResponse> {
        try {
            return await client.post('baskets', { json: payload }).json<BasketResponse>()
        } catch (error) {
            throw await toApiError(error)
        }
    },
    async getPerformance(config: BasketConfig): Promise<PerformanceResponse> {
        try {
            return await client.post('analytics/performance', { json: config }).json<PerformanceResponse>()
        } catch (error) {
            throw await toApiError(error)
        }
    },
    async getWeights(config: BasketConfig): Promise<WeightsResponse> {
        try {
            return await client.post('analytics/weights', { json: config }).json<WeightsResponse>()
        } catch (error) {
            throw await toApiError(error)
        }
    },
    async getRisk(config: BasketConfig): Promise<RiskResponse> {
        try {
            return await client.post('analytics/risk', { json: config }).json<RiskResponse>()
        } catch (error) {
            throw await toApiError(error)
        }
    },
    async getCorrelation(config: BasketConfig): Promise<CorrelationResponse> {
        try {
            return await client
                .post('analytics/correlation', { json: config })
                .json<CorrelationResponse>()
        } catch (error) {
            throw await toApiError(error)
        }
    },
}
