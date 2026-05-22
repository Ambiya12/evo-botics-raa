interface SkeletonProps {
  rows?: number;
}

export function DashboardSkeleton({ rows = 5 }: SkeletonProps) {
  return (
    <div className="skeleton-stack" aria-label="Loading dashboard data">
      {Array.from({ length: rows }, (_, index) => (
        <div className="skeleton-row" key={index}>
          <span />
          <strong />
        </div>
      ))}
    </div>
  );
}
