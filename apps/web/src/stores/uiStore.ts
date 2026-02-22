import { create } from 'zustand'

export type TabId = 'performance' | 'weights' | 'risk' | 'correlation'

interface UiState {
    activeTab: TabId
    sidebarCollapsed: boolean
    setActiveTab: (tab: TabId) => void
    setSidebarCollapsed: (collapsed: boolean) => void
}

export const useUiStore = create<UiState>((set) => ({
    activeTab: 'performance',
    sidebarCollapsed: false,
    setActiveTab: (tab) => set({ activeTab: tab }),
    setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
}))
