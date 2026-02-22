import { useEffect } from 'react'

import { ErrorBoundary } from './components/ErrorBoundary'
import { BasketSidebar } from './features/basket/BasketSidebar'
import { CorrelationTab } from './features/correlation/CorrelationTab'
import { FactorsTab } from './features/factors/FactorsTab'
import { PerformanceTab } from './features/performance/PerformanceTab'
import { RiskTab } from './features/risk/RiskTab'
import { WeightsTab } from './features/weights/WeightsTab'
import { useHealthQuery } from './hooks/useAnalyticsQueries'
import { APP_NAME, TAB_OPTIONS } from './lib/constants'
import { fmtDate } from './lib/formatters'
import { useBasketStore } from './stores/basketStore'
import { useUiStore } from './stores/uiStore'
import type { BasketConfig } from './types/domain'

function App(): JSX.Element {
    const { basketId, config } = useBasketStore()
    const healthQuery = useHealthQuery()
    const { activeTab, setActiveTab, sidebarCollapsed, setSidebarCollapsed } = useUiStore()

    const runtimeConfig: BasketConfig | null = basketId ? { ...config, basket_id: basketId } : null
    const dataFreshness = healthQuery.data?.data_freshness ?? null
    const dataFreshnessLabel = dataFreshness ? fmtDate(dataFreshness) : 'Unavailable'
    const freshnessAgeHours = dataFreshness
        ? Math.floor((Date.now() - new Date(dataFreshness).getTime()) / (1000 * 60 * 60))
        : null
    const showStaleBanner = freshnessAgeHours !== null && freshnessAgeHours > 24

    useEffect(() => {
        const applyResponsiveSidebar = (): void => {
            if (window.innerWidth < 1024) {
                setSidebarCollapsed(true)
            }
        }

        applyResponsiveSidebar()
        window.addEventListener('resize', applyResponsiveSidebar)
        return () => window.removeEventListener('resize', applyResponsiveSidebar)
    }, [setSidebarCollapsed])

    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent): void => {
            const isCommandPaletteShortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k'
            if (!isCommandPaletteShortcut) {
                return
            }

            event.preventDefault()
            setSidebarCollapsed(false)
            const input = document.getElementById('instrument-search-input') as HTMLInputElement | null
            input?.focus()
        }

        window.addEventListener('keydown', onKeyDown)
        return () => window.removeEventListener('keydown', onKeyDown)
    }, [setSidebarCollapsed])

    return (
        <main className="min-h-screen bg-[#050505] text-[#d7d7d7]">
            <header className="border-b border-[#1a1a1a] bg-[#080808] px-4 py-3">
                <div className="mx-auto flex max-w-[1400px] items-center justify-between">
                    <div>
                        <h1 className="text-lg font-semibold tracking-[0.08em]">{APP_NAME}</h1>
                        <p className="ui-label mt-1">Data as of: {dataFreshnessLabel}</p>
                    </div>
                    <button
                        type="button"
                        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                        className="rounded-sm border border-[#1a1a1a] bg-[#050505] px-3 py-1 text-xs text-[#d7d7d7] transition-colors duration-150 hover:bg-[#0d0d0d]"
                    >
                        {sidebarCollapsed ? 'Show Sidebar' : 'Hide Sidebar'}
                    </button>
                </div>
            </header>

            {showStaleBanner ? (
                <div className="border-b border-[#f5a623] px-4 py-2 text-sm text-[#f5a623]">
                    Warning: data appears stale ({freshnessAgeHours}h old). Refresh ingestion before relying on analytics.
                </div>
            ) : null}

            <div className="mx-auto grid max-w-[1400px] grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[340px_1fr]">
                {!sidebarCollapsed ? <BasketSidebar /> : <div />}

                <section className="space-y-4">
                    <nav className="flex flex-wrap gap-2">
                        {TAB_OPTIONS.map((tab) => (
                            <button
                                key={tab.id}
                                type="button"
                                onClick={() => setActiveTab(tab.id)}
                                className={`rounded-sm border px-3 py-1 text-sm transition-colors duration-150 ${tab.id === activeTab
                                    ? 'border-[#00ff9d] text-[#00ff9d] shadow-[0_0_8px_rgba(0,255,157,0.22)]'
                                    : 'border-[#1a1a1a] bg-[#080808] text-[#8a8a8a] hover:bg-[#0d0d0d] hover:text-[#d7d7d7]'
                                    }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </nav>

                    {runtimeConfig === null ? (
                        <div className="rounded border border-dashed border-[#1a1a1a] bg-[#080808] p-8 text-center text-[#8a8a8a]">
                            Add at least one leg, then click <span className="font-semibold text-[#d7d7d7]">Apply Basket</span> to load analytics.
                        </div>
                    ) : null}

                    {runtimeConfig !== null && activeTab === 'performance' ? (
                        <ErrorBoundary>
                            <PerformanceTab config={runtimeConfig} />
                        </ErrorBoundary>
                    ) : null}

                    {runtimeConfig !== null && activeTab === 'weights' ? (
                        <ErrorBoundary>
                            <WeightsTab config={runtimeConfig} />
                        </ErrorBoundary>
                    ) : null}

                    {runtimeConfig !== null && activeTab === 'risk' ? (
                        <ErrorBoundary>
                            <RiskTab config={runtimeConfig} />
                        </ErrorBoundary>
                    ) : null}

                    {runtimeConfig !== null && activeTab === 'correlation' ? (
                        <ErrorBoundary>
                            <CorrelationTab config={runtimeConfig} />
                        </ErrorBoundary>
                    ) : null}

                    {runtimeConfig !== null && activeTab === 'factors' ? (
                        <ErrorBoundary>
                            <FactorsTab config={runtimeConfig} />
                        </ErrorBoundary>
                    ) : null}
                </section>
            </div>
        </main>
    )
}

export default App
