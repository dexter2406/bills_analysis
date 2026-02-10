import { StatusBadge } from "./StatusBadge";

const steps = ["idle", "ready", "creating", "tracking", "review_ready", "review_submitting", "done", "failed"];

/**
 * Flow status panel emphasizing workflow visibility.
 * @param {{
 *  phase: string;
 *  batch: { status: "queued" | "running" | "review_ready" | "merging" | "merged" | "failed"; batch_id: string } | null;
 *  variant?: "panel" | "rail";
 * }} props
 */
export function FlowStatusPanel({ phase, batch, variant = "panel" }) {
  const activeIndex = steps.indexOf(phase);
  const railSteps = ["idle", "ready", "creating", "tracking", "review", "submit", "done", "failed"];

  if (variant === "rail") {
    return (
      <section className="workflow-rail section-enter">
        <header className="workflow-rail-header">
          <span className="workflow-rail-title">Workflow</span>
          <span className={`status-dot ${phase === "tracking" || phase === "creating" ? "pulse" : ""}`} />
        </header>

        <div className="workflow-rail-body">
          {steps.map((step, index) => {
            const stepState = index < activeIndex ? "done" : index === activeIndex ? "active" : "pending";
            return (
              <div key={step} className="workflow-rail-row">
                <span className={`workflow-rail-dot ${stepState}`} />
                <div className="workflow-rail-text">
                  <p>{railSteps[index]}</p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="workflow-rail-footer">
          <StatusBadge status={batch?.status} />
        </div>
      </section>
    );
  }

  return (
    <section className="ledger-card section-enter p-4">
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-semibold">Workflow Status</h3>
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.08em] text-ledger-smoke">
          <span className={`status-dot ${phase === "tracking" || phase === "creating" ? "pulse" : ""}`} />
          {phase}
        </div>
      </header>

      <div className="mb-3 rounded-md border border-ledger-line bg-slate-50 px-3 py-2 text-sm text-ledger-smoke">
        <div className="flex items-center justify-between gap-2">
          <span>Backend Status</span>
          <StatusBadge status={batch?.status} />
        </div>
        {batch ? <p className="mt-1 text-xs">Batch ID: {batch.batch_id}</p> : null}
      </div>

      <div className="step-grid">
        {steps.map((step, index) => {
          const stepState = index < activeIndex ? "done" : index === activeIndex ? "active" : "pending";
          return (
            <div key={step} className="step-row">
              <span className={stepState === "active" ? "font-semibold text-ledger-ink" : "text-ledger-smoke"}>{step}</span>
              <span className={`step-chip ${stepState}`}>{stepState}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
