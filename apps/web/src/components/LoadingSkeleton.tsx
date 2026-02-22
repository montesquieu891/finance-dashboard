interface LoadingSkeletonProps {
    className?: string
}

export function LoadingSkeleton({ className }: LoadingSkeletonProps): JSX.Element {
    return <div className={`animate-pulse rounded-sm bg-[#0d0d0d] ${className ?? ''}`} />
}
