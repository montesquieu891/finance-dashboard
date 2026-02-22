import React from 'react'

interface Props {
    children: React.ReactNode
}

interface State {
    hasError: boolean
    message: string
}

export class ErrorBoundary extends React.Component<Props, State> {
    public constructor(props: Props) {
        super(props)
        this.state = { hasError: false, message: '' }
    }

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, message: error.message }
    }

    public componentDidCatch(_error: Error): void {
        // Intentionally empty for MVP stage.
    }

    private reset = (): void => {
        this.setState({ hasError: false, message: '' })
    }

    public render(): React.ReactNode {
        if (this.state.hasError) {
            return (
                <div className="rounded border border-[#ff3d5a] bg-[#080808] p-4 text-sm text-[#ff3d5a]">
                    <p className="font-medium uppercase tracking-[0.12em]">Panel failed to render.</p>
                    <p className="mt-1">{this.state.message || 'Unexpected error'}</p>
                    <button
                        type="button"
                        onClick={this.reset}
                        className="mt-3 rounded-sm border border-[#1a1a1a] bg-[#050505] px-3 py-1 text-xs font-medium text-[#d7d7d7] transition-colors duration-150 hover:bg-[#0d0d0d]"
                    >
                        Retry
                    </button>
                </div>
            )
        }

        return this.props.children
    }
}
