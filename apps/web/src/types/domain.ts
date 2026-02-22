import type { components, operations } from './api.generated'

export type Instrument = components['schemas']['InstrumentResponse']
export type BasketLegCreate = components['schemas']['BasketLegCreate']
export type BasketCreateRequest = components['schemas']['BasketCreateRequest']
export type BasketResponse = components['schemas']['BasketResponse']
export type BasketConfig = components['schemas']['BasketConfigRequest']
export type PerformanceResponse = components['schemas']['PerformanceResponse']
export type WeightsResponse = components['schemas']['WeightsResponse']
export type RiskResponse = components['schemas']['RiskResponse']
export type CorrelationResponse = components['schemas']['CorrelationResponse']
export type RiskMetrics = components['schemas']['RiskMetrics']
export type WeightMethod = components['schemas']['BasketConfigRequest']['weight_method']
export type PricePoint = components['schemas']['PriceDailyResponse']

export type SearchInstrumentsResponse =
    operations['search_instruments_api_v1_instruments_search_get']['responses'][200]['content']['application/json']

export interface HealthResponse {
    status: string
    db: string
    redis: string
    environment: string
    data_freshness?: string | null
}
