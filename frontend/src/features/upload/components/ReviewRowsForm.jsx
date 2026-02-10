import { Button } from "../../../shared/ui/Button";

/**
 * Review rows editor and submit trigger.
 * @param {{
 *  value: string;
 *  disabled?: boolean;
 *  onChange: (value: string) => void;
 *  onSubmit: () => Promise<boolean>;
 * }} props
 */
export function ReviewRowsForm({ value, disabled = false, onChange, onSubmit }) {
  return (
    <section className="ledger-card section-enter p-4">
      <header className="mb-2 flex items-center justify-between">
        <h3 className="text-lg font-semibold">Review Rows</h3>
        <span className="text-xs uppercase tracking-[0.08em] text-ledger-smoke">JSON</span>
      </header>

      <textarea
        className="min-h-36 w-full rounded-md border border-ledger-line bg-white p-3 text-sm text-ledger-ink outline-none ring-blue-200 transition focus:ring-2"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        aria-label="review rows"
      />

      <div className="mt-3 flex gap-2">
        <Button type="button" variant="primary" disabled={disabled} onClick={() => void onSubmit()}>
          Submit Review + Queue Merge
        </Button>
      </div>
    </section>
  );
}
