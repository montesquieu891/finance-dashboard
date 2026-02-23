import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../lib/api'
import { apiBaseUrl } from '../lib/constants'
import type { AlertRuleCreateRequest, LivePriceEnvelope } from '../types/domain'

type LiveConnectionState = 'connecting' | 'connected' | 'disconnected'

const toWsUrl = (basketId: string | null): string => {
    const configuredApi = import.meta.env.VITE_API_BASE_URL ?? apiBaseUrl
    const apiKey = import.meta.env.VITE_API_KEY ?? 'dev-api-key'

    if (configuredApi.startsWith('http://') || configuredApi.startsWith('https://')) {
        const parsed = new URL(configuredApi)
        const protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:'
        return `${protocol}//${parsed.host}/ws/prices?api_key=${encodeURIComponent(apiKey)}${basketId ? `&basket_id=${encodeURIComponent(basketId)}` : ''}`
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/prices?api_key=${encodeURIComponent(apiKey)}${basketId ? `&basket_id=${encodeURIComponent(basketId)}` : ''}`
}

export const useLivePrices = (basketId: string | null) => {
    const [connectionState, setConnectionState] = useState<LiveConnectionState>('connecting')
    const [pricesBySymbol, setPricesBySymbol] = useState<Record<string, { price: number; asOf: string }>>({})
    const reconnectDelayMsRef = useRef(1000)
    const reconnectTimerRef = useRef<number | null>(null)

    useEffect(() => {
        let socket: WebSocket | null = null
        let isUnmounted = false

        const connect = (): void => {
            setConnectionState('connecting')
            socket = new WebSocket(toWsUrl(basketId))

            socket.onopen = () => {
                reconnectDelayMsRef.current = 1000
                if (!isUnmounted) {
                    setConnectionState('connected')
                }
            }

            socket.onmessage = (event) => {
                try {
                    const payload = JSON.parse(event.data) as LivePriceEnvelope
                    if (payload.type !== 'price_tick') {
                        return
                    }

                    setPricesBySymbol((previous) => {
                        const next = { ...previous }
                        for (const item of payload.data) {
                            next[item.symbol] = {
                                price: Number(item.price),
                                asOf: item.as_of,
                            }
                        }
                        return next
                    })
                } catch {
                    // no-op
                }
            }

            socket.onclose = () => {
                if (isUnmounted) {
                    return
                }
                setConnectionState('disconnected')
                const delay = reconnectDelayMsRef.current
                reconnectDelayMsRef.current = Math.min(10_000, reconnectDelayMsRef.current * 2)
                reconnectTimerRef.current = window.setTimeout(connect, delay)
            }

            socket.onerror = () => {
                socket?.close()
            }
        }

        connect()

        return () => {
            isUnmounted = true
            if (reconnectTimerRef.current !== null) {
                window.clearTimeout(reconnectTimerRef.current)
            }
            socket?.close()
        }
    }, [basketId])

    return useMemo(
        () => ({
            connectionState,
            pricesBySymbol,
        }),
        [connectionState, pricesBySymbol],
    )
}

export const useAlertRulesQuery = (basketId: string | null) =>
    useQuery({
        queryKey: ['live', 'alerts', basketId],
        queryFn: () => {
            if (!basketId) {
                throw new Error('Basket ID is missing')
            }
            return api.listAlertRules(basketId)
        },
        enabled: basketId !== null,
    })

export const useCreateAlertRule = (basketId: string | null) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (payload: AlertRuleCreateRequest) => {
            if (!basketId) {
                throw new Error('Basket ID is missing')
            }
            return api.createAlertRule(basketId, payload)
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ['live', 'alerts', basketId] })
        },
    })
}

export const useDeleteAlertRule = (basketId: string | null) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (alertId: string) => api.deleteAlertRule(alertId),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ['live', 'alerts', basketId] })
        },
    })
}

export const usePositionsQuery = (basketId: string | null) =>
    useQuery({
        queryKey: ['live', 'positions', basketId],
        queryFn: () => {
            if (!basketId) {
                throw new Error('Basket ID is missing')
            }
            return api.getPositions(basketId)
        },
        enabled: basketId !== null,
        refetchInterval: 60_000,
    })

export const useUploadPositions = (basketId: string | null) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (file: File) => {
            if (!basketId) {
                throw new Error('Basket ID is missing')
            }
            return api.uploadPositionsCsv(basketId, file)
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ['live', 'positions', basketId] })
        },
    })
}
