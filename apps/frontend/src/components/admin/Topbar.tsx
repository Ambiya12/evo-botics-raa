import { Bell, RefreshCw, Search } from "lucide-react";

interface TopbarProps {
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  lastSyncedAt: string | null;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export function Topbar({
  searchQuery,
  onSearchQueryChange,
  lastSyncedAt,
  isRefreshing,
  onRefresh,
}: TopbarProps) {
  return (
    <header className="topbar">
      <div>
        <p className="section-kicker">Operator console</p>
        <h2>Robot monitoring dashboard</h2>
        <p className="topbar__meta">
          {lastSyncedAt ? `Last synced ${lastSyncedAt}` : "Preparing live telemetry"}
        </p>
      </div>

      <div className="topbar__actions">
        <label className="search" htmlFor="dashboard-search">
          <Search aria-hidden="true" size={17} strokeWidth={1.8} />
          <input
            id="dashboard-search"
            placeholder="Filter events and incidents"
            type="search"
            value={searchQuery}
            onChange={(event) => onSearchQueryChange(event.target.value)}
          />
        </label>
        <button
          className="icon-button"
          type="button"
          aria-label="Refresh dashboard data"
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw aria-hidden="true" size={18} className={isRefreshing ? "spin" : ""} />
        </button>
        <button className="icon-button" type="button" aria-label="Open notifications">
          <Bell aria-hidden="true" size={18} />
        </button>
      </div>
    </header>
  );
}
