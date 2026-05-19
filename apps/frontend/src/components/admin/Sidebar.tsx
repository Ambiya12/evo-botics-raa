import { memo } from "react";
import { navigationItems } from "../../data/mockAdminData";

export const Sidebar = memo(function Sidebar() {
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
            className={`nav-list__item ${item.active ? "nav-list__item--active" : ""}`}
            key={item.label}
            type="button"
            aria-current={item.active ? "page" : undefined}
          >
            <item.icon aria-hidden="true" size={17} strokeWidth={1.8} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
});
