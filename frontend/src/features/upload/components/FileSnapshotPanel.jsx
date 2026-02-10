/**
 * Pending review table shown in the right-side panel.
 * @param {{
 *  files: Array<{ name: string; category: string | null }>;
 *  batchStatus?: "queued" | "running" | "review_ready" | "merging" | "merged" | "failed";
 * }} props
 */
export function FileSnapshotPanel({ files, batchStatus }) {
  const rows = files.slice(0, 8).map((file, index) => ({
    id: `${file.name}-${index}`,
    source: file.name,
    date: "--",
    brutto: "--",
    netto: "--",
    status: mapRowStatus(batchStatus),
  }));

  return (
    <section className="ledger-card section-enter p-4 review-primary">
      <header className="mb-2 flex items-center justify-between">
        <h3 className="text-lg font-semibold">Pending Review Items</h3>
        <span className="text-xs text-ledger-smoke">{rows.length} items</span>
      </header>
      <p className="mb-3 text-xs text-ledger-smoke">Rows generated after upload, used for manual verification before review submission.</p>

      {rows.length ? (
        <div className="overflow-x-auto rounded-md border border-ledger-line">
          <table className="queue-table">
            <thead>
              <tr>
                <th>Store / Sender</th>
                <th>Date</th>
                <th>Brutto</th>
                <th>Netto</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className="truncate text-ledger-ink">{row.source}</td>
                  <td className="text-ledger-smoke">{row.date}</td>
                  <td className="text-ledger-smoke">{row.brutto}</td>
                  <td className="text-ledger-smoke">{row.netto}</td>
                  <td>
                    <span
                      className={`rounded-full border px-2 py-1 text-[0.68rem] font-semibold ${
                        row.status === "review needed"
                          ? "border-amber-200 bg-amber-50 text-amber-700"
                          : row.status === "approved"
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                            : row.status === "failed"
                              ? "border-red-200 bg-red-50 text-red-700"
                              : "border-blue-200 bg-blue-50 text-blue-700"
                      }`}
                    >
                      {row.status}
                    </span>
                  </td>
                  <td className="text-xs text-blue-700">View</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-ledger-smoke">No pending review rows yet.</p>
      )}
    </section>
  );
}

/**
 * Map backend batch status to row-level review label for UI-only table.
 * @param {"queued" | "running" | "review_ready" | "merging" | "merged" | "failed" | undefined} batchStatus
 */
function mapRowStatus(batchStatus) {
  if (!batchStatus) {
    return "not submitted";
  }
  if (batchStatus === "review_ready") {
    return "review needed";
  }
  if (batchStatus === "merged") {
    return "approved";
  }
  if (batchStatus === "failed") {
    return "failed";
  }
  return "queued";
}
