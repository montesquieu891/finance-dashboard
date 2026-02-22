import { ErrorBoundary } from './components/ErrorBoundary'
import { BasketSidebar } from './features/basket/BasketSidebar'
import { CorrelationTab } from './features/correlation/CorrelationTab'
import { PerformanceTab } from './features/performance/PerformanceTab'
import { RiskTab } from './features/risk/RiskTab'
import { WeightsTab } from './features/weights/WeightsTab'
import { APP_NAME, TAB_OPTIONS } from './lib/constants'
import { useBasketStore } from './stores/basketStore'
import { useUiStore } from './stores/uiStore'
import type { BasketConfig } from './types/domain'

function App(): JSX.Element {
    const { basketId, config } = useBasketStore()
    const { activeTab, setActiveTab, sidebarCollapsed, setSidebarCollapsed } = useUiStore()

    const runtimeConfig: BasketConfig | null = basketId ? { ...config, basket_id: basketId } : null

    return (
        <main className="min-h-screen bg-slate-950 text-slate-100">
            <header className="border-b border-slate-800 px-4 py-3">
                <div className="mx-auto flex max-w-[1400px] items-center justify-between">
                    <h1 className="text-xl font-semibold">{APP_NAME}</h1>
                    <button
                        type="button"
                        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                        className="rounded border border-slate-700 px-3 py-1 text-xs text-slate-200"
                    >
                        {sidebarCollapsed ? 'Show Sidebar' : 'Hide Sidebar'}
                    </button>
                </div>
            </header>

            <div className="mx-auto grid max-w-[1400px] grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[340px_1fr]">
                {!sidebarCollapsed ? <BasketSidebar /> : <div />}

                <section className="space-y-4">
                    <nav className="flex flex-wrap gap-2">
                        {TAB_OPTIONS.map((tab) => (
                            <button
                                key={tab.id}
                                type="button"
                                onClick={() => setActiveTab(tab.id)}
                                className={`rounded px-3 py-1 text-sm ${tab.id === activeTab ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-300'
                                    }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </nav>

                    {runtimeConfig === null ? (
                        <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900 p-8 text-center text-slate-400">
                            Add at least one leg, then click <span className="font-semibold text-slate-200">Apply Basket</span> to load analytics.
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
                </section>
            </div>
        </main>
    )
}

export default App
