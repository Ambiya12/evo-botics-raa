import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface AdminShellProps {
  children: ReactNode;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  lastSyncedAt: string | null;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export function AdminShell({
  children,
  searchQuery,
  onSearchQueryChange,
  lastSyncedAt,
  isRefreshing,
  onRefresh,
}: AdminShellProps) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="dashboard">
        <Topbar
          searchQuery={searchQuery}
          onSearchQueryChange={onSearchQueryChange}
          lastSyncedAt={lastSyncedAt}
          isRefreshing={isRefreshing}
          onRefresh={onRefresh}
        />
        {children}
      </main>
    </div>
  );
}
