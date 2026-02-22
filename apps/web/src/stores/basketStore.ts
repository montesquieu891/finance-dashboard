import { create } from 'zustand'

import type { BasketConfig, Instrument } from '../types/domain'

export interface DraftLeg {
    instrument_id: string
    side: 'long' | 'short'
    weight_override?: number | null
    instrument: Instrument
}

export interface BasketConfigDraft extends Omit<BasketConfig, 'basket_id'> { }

interface BasketState {
    basketId: string | null
    basketName: string
    basketDescription: string
    legs: DraftLeg[]
    searchQuery: string
    config: BasketConfigDraft
    setSearchQuery: (query: string) => void
    addLeg: (instrument: Instrument, side: 'long' | 'short') => void
    removeLeg: (instrumentId: string, side: 'long' | 'short') => void
    setLegWeightOverride: (instrumentId: string, side: 'long' | 'short', value: number | null) => void
    setBasketMeta: (name: string, description: string) => void
    setConfig: <K extends keyof BasketConfigDraft>(key: K, value: BasketConfigDraft[K]) => void
    setBasketId: (basketId: string | null) => void
}

const today = new Date()
const start = new Date(today)
start.setFullYear(today.getFullYear() - 1)

const toIsoDate = (value: Date): string => value.toISOString().slice(0, 10)

const defaultConfig: BasketConfigDraft = {
    weight_method: 'equal',
    gross_exposure: 1,
    start_date: toIsoDate(start),
    end_date: toIsoDate(today),
    benchmark_id: null,
    lookback_days: 90,
    include_funding_adj: true,
    include_trading_costs: true,
    fee_bps: 4,
    slippage_bps: 6,
    rebalance_freq: 'none',
}

export const useBasketStore = create<BasketState>((set) => ({
    basketId: null,
    basketName: 'My Basket',
    basketDescription: '',
    legs: [],
    searchQuery: '',
    config: defaultConfig,
    setSearchQuery: (query) => set({ searchQuery: query }),
    addLeg: (instrument, side) =>
        set((state) => {
            const exists = state.legs.some(
                (leg) => leg.instrument_id === instrument.id && leg.side === side,
            )
            if (exists) {
                return state
            }

            return {
                ...state,
                basketId: null,
                legs: [
                    ...state.legs,
                    {
                        instrument_id: instrument.id,
                        side,
                        weight_override: null,
                        instrument,
                    },
                ],
            }
        }),
    removeLeg: (instrumentId, side) =>
        set((state) => ({
            ...state,
            basketId: null,
            legs: state.legs.filter((leg) => !(leg.instrument_id === instrumentId && leg.side === side)),
        })),
    setLegWeightOverride: (instrumentId, side, value) =>
        set((state) => ({
            ...state,
            basketId: null,
            legs: state.legs.map((leg) => {
                if (leg.instrument_id === instrumentId && leg.side === side) {
                    return { ...leg, weight_override: value }
                }
                return leg
            }),
        })),
    setBasketMeta: (name, description) => set({ basketName: name, basketDescription: description }),
    setConfig: (key, value) =>
        set((state) => ({
            ...state,
            config: {
                ...state.config,
                [key]: value,
            },
        })),
    setBasketId: (basketId) => set({ basketId }),
}))
