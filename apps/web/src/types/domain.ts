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

export interface LivePriceTick {
    symbol: string
    price: string
    as_of: string
}

export interface LivePriceEnvelope {
    type: 'price_tick'
    basket_id: string | null
    generated_at: string
    data: LivePriceTick[]
}

export interface AlertRule {
    id: string
    basket_id: string
    instrument_id: string | null
    name: string
    rule_type: 'drawdown' | 'leg_stop'
    threshold: string
    cooldown_minutes: number
    is_active: boolean
    last_triggered_at: string | null
    created_at: string
}

export interface AlertRuleCreateRequest {
    name: string
    rule_type: 'drawdown' | 'leg_stop'
    threshold: number
    cooldown_minutes: number
    is_active: boolean
    instrument_id?: string | null
}

export interface PositionSnapshot {
    id: string
    instrument_id: string
    symbol: string
    quantity: string
    avg_price: string | null
    last_price: string | null
    model_signed_weight: number
    actual_signed_weight: number
    drift_bps: number
    daily_pnl: string | null
    uploaded_at: string
}

export interface PositionsSummary {
    gross_notional: string
    net_notional: string
    drift_l1: number
    daily_pnl_total: string
}

export interface PositionsResponse {
    rows: PositionSnapshot[]
    summary: PositionsSummary
}
