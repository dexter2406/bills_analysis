/**
 * Reusable text input with label and optional hint.
 * @param {{
 *  id: string;
 *  label: string;
 *  hint?: string;
 * } & import("react").InputHTMLAttributes<HTMLInputElement>} props
 */
export function InputField({ id, label, hint, ...rest }) {
  return (
    <label htmlFor={id} className="flex w-full flex-col gap-1 text-sm text-ledger-smoke">
      <span className="font-semibold uppercase tracking-[0.12em] text-[0.68rem] text-ledger-ink">{label}</span>
      <input
        id={id}
        className="w-full rounded-md border border-ledger-line bg-white/80 px-3 py-2 text-sm text-ledger-ink outline-none ring-amber-200 transition focus:ring-2"
        {...rest}
      />
      {hint ? <span className="text-xs text-ledger-smoke">{hint}</span> : null}
    </label>
  );
}
