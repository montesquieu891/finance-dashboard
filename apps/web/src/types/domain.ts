import type { components, operations } from './api.generated'

export type Instrument = components['schemas']['InstrumentResponse'] & {
    ingesting?: boolean
}
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

export interface InstrumentIngestionStatusResponse {
    status: 'complete' | 'ingesting' | 'failed'
    rows: number
    last_updated: string | null
}

export interface FactorDefinition {
    code: string
    name: string
    category: string
    proxy_symbol: string
}

export interface FactorsRequest {
    config: BasketConfig
    factor_codes?: string[]
    rolling_window?: number
}

export interface FactorExposurePoint {
    date: string
    exposures: Record<string, number>
    alpha: number
    r2: number
    regime: string
}

export interface FactorAttributionPoint {
    factor: string
    contribution: number
}

export interface FactorCorrelation {
    factors: string[]
    matrix: number[][]
}

export interface FactorsResponse {
    factors: FactorDefinition[]
    exposures: FactorExposurePoint[]
    attribution: FactorAttributionPoint[]
    factor_correlation: FactorCorrelation
}
