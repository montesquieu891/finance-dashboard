import type { TabId } from '../stores/uiStore'
import type { BasketConfig } from '../types/domain'

export const APP_NAME = 'Basket Monitor'
export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export const WEIGHT_METHODS: Array<{ value: BasketConfig['weight_method']; label: string }> = [
    { value: 'equal', label: 'Equal Weight' },
    { value: 'inverse_vol', label: 'Inverse Volatility' },
    { value: 'inverse_corr', label: 'Inverse Correlation' },
    { value: 'risk_parity', label: 'Risk Parity' },
    { value: 'beta_adjusted', label: 'Beta Adjusted' },
    { value: 'market_cap', label: 'Market Cap' },
    { value: 'manual', label: 'Manual' },
]

export const REBALANCE_FREQS: Array<{ value: BasketConfig['rebalance_freq']; label: string }> = [
    { value: 'none', label: 'None' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly' },
    { value: 'monthly', label: 'Monthly' },
]

export const TAB_OPTIONS: Array<{ id: TabId; label: string }> = [
    { id: 'performance', label: 'Performance' },
    { id: 'weights', label: 'Weights' },
    { id: 'risk', label: 'Risk' },
    { id: 'correlation', label: 'Correlation' },
    { id: 'factors', label: 'Factors' },
]
