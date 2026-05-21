import { memo } from "react";
import { navigationItems } from "../../data/mockAdminData";

interface SidebarProps {
  activePage: string;
  onNavigate: (id: string) => void;
}

export const Sidebar = memo(function Sidebar({ activePage, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Admin navigation">
      <div className="brand">
        <div className="brand__mark" aria-hidden="true">
          EB
        </div>
        <div>
          <p className="brand__eyebrow">Evo-Botics</p>
          <h1>Admin</h1>
        </div>
      </div>

      <nav className="nav-list">
        {navigationItems.map((item) => (
          <button
            className={`nav-list__item ${item.id === activePage ? "nav-list__item--active" : ""}`}
            key={item.id}
            type="button"
            aria-current={item.id === activePage ? "page" : undefined}
            onClick={() => onNavigate(item.id)}
          >
            <item.icon aria-hidden="true" size={17} strokeWidth={1.8} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
});
