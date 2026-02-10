import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Upload Management", to: "/" },
  { label: "Manual Review", to: "/manual-review" },
  { label: "Archive", to: "/archive" },
  { label: "Settings", to: "/settings" },
];

/**
 * Shared application frame with sidebar navigation.
 * @param {{ children: import("react").ReactNode }} props
 */
export function AppFrame({ children }) {
  return (
    <main className="app-layout">
      <aside className="app-sidebar">
        <div className="app-brand">
          <span className="app-brand-icon">IH</span>
          <span>InvoiceHub</span>
        </div>
        <nav className="app-nav">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => `app-nav-item ${isActive ? "active" : ""}`}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="app-main">{children}</div>
    </main>
  );
}
