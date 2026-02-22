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
                <div className="rounded-lg border border-rose-500/50 bg-rose-950/30 p-4 text-sm text-rose-200">
                    <p className="font-medium">Panel failed to render.</p>
                    <p className="mt-1">{this.state.message || 'Unexpected error'}</p>
                    <button
                        type="button"
                        onClick={this.reset}
                        className="mt-3 rounded bg-rose-700 px-3 py-1 text-xs font-medium text-white"
                    >
                        Retry
                    </button>
                </div>
            )
        }

        return this.props.children
    }
}
