import { AppFrame } from "./AppFrame";

/**
 * Lightweight placeholder page for non-M1 sections.
 * @param {{ title: string; description: string }} props
 */
export function PlaceholderPage({ title, description }) {
  return (
    <AppFrame>
      <header className="app-topbar section-enter">
        <div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </header>
    </AppFrame>
  );
}

