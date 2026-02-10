/**
 * Lightweight preview placeholder panel loaded lazily.
 * @param {{ fileName?: string }} props
 */
export function PreviewPanel({ fileName }) {
  return (
    <section className="ledger-card section-enter p-4">
      <h3 className="text-xl">Preview</h3>
      <div className="mt-3 rounded-md border border-ledger-line bg-white/75 p-3">
        <p className="text-sm font-semibold text-ledger-ink">{fileName || "No file selected"}</p>
        <p className="mt-2 text-xs text-ledger-smoke">
          M1 keeps preview as a placeholder. Real PDF rendering can be wired with a dedicated viewer after backend storage URLs are available.
        </p>
      </div>
    </section>
  );
}
