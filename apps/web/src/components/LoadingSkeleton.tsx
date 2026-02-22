interface LoadingSkeletonProps {
    className?: string
}

export function LoadingSkeleton({ className }: LoadingSkeletonProps): JSX.Element {
    return <div className={`animate-pulse rounded-md bg-slate-700/60 ${className ?? ''}`} />
}
