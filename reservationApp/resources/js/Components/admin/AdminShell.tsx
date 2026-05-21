import type { ReactNode } from "react";
import type { ConnectionStatus } from "../../types/admin";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface AdminShellProps {
  children: ReactNode;
  activePage: string;
  onNavigate: (id: string) => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  lastSyncedAt: string | null;
  isRefreshing: boolean;
  onRefresh: () => void;
  connectionStatus: ConnectionStatus;
}

export function AdminShell({
  children,
  activePage,
  onNavigate,
  searchQuery,
  onSearchQueryChange,
  lastSyncedAt,
  isRefreshing,
  onRefresh,
  connectionStatus,
}: AdminShellProps) {
  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onNavigate={onNavigate} />
      <main className="dashboard">
        <Topbar
          searchQuery={searchQuery}
          onSearchQueryChange={onSearchQueryChange}
          lastSyncedAt={lastSyncedAt}
          isRefreshing={isRefreshing}
          onRefresh={onRefresh}
          connectionStatus={connectionStatus}
        />
        {children}
      </main>
    </div>
  );
}
