import { Button } from "../../../shared/ui/Button";

/**
 * Batch type switcher for Daily/Office workflow.
 * @param {{
 *  value: "daily" | "office";
 *  onChange: (value: "daily" | "office") => void;
 * }} props
 */
export function BatchTypeSelector({ value, onChange }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-ledger-ink">Batch Type</p>
      <div className="flex gap-2">
        <Button
          type="button"
          variant={value === "daily" ? "primary" : "ghost"}
          onClick={() => onChange("daily")}
          aria-pressed={value === "daily"}
          className="min-w-20"
        >
          Daily
        </Button>
        <Button
          type="button"
          variant={value === "office" ? "primary" : "ghost"}
          onClick={() => onChange("office")}
          aria-pressed={value === "office"}
          className="min-w-20"
        >
          Office
        </Button>
      </div>
    </div>
  );
}
