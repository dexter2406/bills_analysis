import { useMemo, useState } from "react";
import { Button } from "../../../shared/ui/Button";

/**
 * Inline run-date picker using native date input popover.
 * @param {{
 *  value: string;
 *  onChange: (nextValue: string) => void;
 * }} props
 */
export function RunDatePicker({ value, onChange }) {
  const [open, setOpen] = useState(false);

  const isoValue = useMemo(() => toIsoDate(value), [value]);

  return (
    <div className="relative flex flex-col gap-1">
      <span className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-ledger-ink">Run Date</span>
      <button
        type="button"
        className="w-full rounded-md border border-ledger-line bg-white px-3 py-2 text-left text-sm text-ledger-ink"
        onClick={() => setOpen((prev) => !prev)}
      >
        {value}
      </button>
      <span className="text-xs text-ledger-smoke">Default is today. Click to change.</span>

      {open ? (
        <div className="absolute right-0 top-[calc(100%+0.4rem)] z-20 w-full rounded-md border border-ledger-line bg-white p-2 shadow-ledger">
          <input
            type="date"
            className="w-full rounded border border-ledger-line bg-white px-2 py-2 text-sm text-ledger-ink"
            value={isoValue}
            onChange={(event) => {
              onChange(fromIsoDate(event.target.value));
              setOpen(false);
            }}
          />
          <div className="mt-2 flex justify-between">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                onChange(formatToday());
                setOpen(false);
              }}
            >
              Today
            </Button>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Close
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Convert DD/MM/YYYY to YYYY-MM-DD for native date input.
 * @param {string} runDate
 */
function toIsoDate(runDate) {
  const parts = runDate.split("/");
  if (parts.length !== 3) {
    return "";
  }
  const [dd, mm, yyyy] = parts;
  if (!dd || !mm || !yyyy) {
    return "";
  }
  return `${yyyy}-${mm}-${dd}`;
}

/**
 * Convert YYYY-MM-DD to DD/MM/YYYY.
 * @param {string} iso
 */
function fromIsoDate(iso) {
  const parts = iso.split("-");
  if (parts.length !== 3) {
    return "";
  }
  const [yyyy, mm, dd] = parts;
  return `${dd}/${mm}/${yyyy}`;
}

/**
 * Format current date as DD/MM/YYYY.
 */
function formatToday() {
  const now = new Date();
  const dd = String(now.getDate()).padStart(2, "0");
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const yyyy = String(now.getFullYear());
  return `${dd}/${mm}/${yyyy}`;
}
