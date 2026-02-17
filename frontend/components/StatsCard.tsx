/**
 * Stats Card Component
 * Displays a metric with label and optional trend
 */

interface StatsCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: string;
}

export function StatsCard({ label, value, sublabel, trend, icon }: StatsCardProps) {
  const trendColors = {
    up: 'text-emerald-600 dark:text-emerald-300',
    down: 'text-rose-600 dark:text-rose-300',
    neutral: 'text-[var(--muted)]',
  };

  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→',
  };

  return (
    <div className="app-card p-5 transition hover:-translate-y-0.5 hover:shadow-xl">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-[var(--muted)]">{label}</p>
          <p className="title-display mt-2 text-3xl font-semibold text-[var(--text)]">{value}</p>

          {sublabel && (
            <p className="mt-2 text-sm text-[var(--muted)]">{sublabel}</p>
          )}
        </div>

        {icon && (
          <div className="text-2xl opacity-60">{icon}</div>
        )}
      </div>

      {trend && (
        <div className={`mt-4 flex items-center text-sm ${trendColors[trend]}`}>
          <span className="font-medium">{trendIcons[trend]}</span>
          <span className="ml-1">
            {trend === 'up' ? 'Trending up' : trend === 'down' ? 'Trending down' : 'Stable'}
          </span>
        </div>
      )}
    </div>
  );
}
