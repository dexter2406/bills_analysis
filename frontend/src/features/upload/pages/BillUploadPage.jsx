import { useNavigate } from "react-router-dom";
import { AppFrame } from "../../../app/AppFrame";
import { BatchTypeSelector } from "../components/BatchTypeSelector";
import { PdfDropzone } from "../components/PdfDropzone";
import { FileQueuePanel } from "../components/FileQueuePanel";
import { RunDatePicker } from "../components/RunDatePicker";
import { StatusBadge } from "../components/StatusBadge";
import { AlertBanner } from "../../../shared/ui/AlertBanner";
import { Button } from "../../../shared/ui/Button";
import { useUploadFlowContext } from "../state/UploadFlowContext";

/**
 * Main M1 upload page focused on file intake and batch creation.
 */
export function BillUploadPage() {
  const navigate = useNavigate();
  const { client, state, actions, flags } = useUploadFlowContext();

  const canGoReview =
    state.batch &&
    (state.batch.status === "review_ready" || state.batch.status === "merging" || state.batch.status === "merged");

  const handleBatchTypeChange = (nextType) => {
    if (nextType === state.batchType) {
      return;
    }
    if (state.files.length) {
      const shouldSwitch = window.confirm("Switching batch type will clear currently loaded files. Continue?");
      if (!shouldSwitch) {
        return;
      }
    }
    actions.setBatchType(nextType);
  };

  return (
    <AppFrame>
      <header className="app-topbar section-enter">
        <div>
          <h1>Upload Site</h1>
          <p>Enterprise workflow for daily/office ingestion, validation, and merge tracking.</p>
        </div>
        <div className="topbar-meta">
          <span className="topbar-chip success">API Connected: v1 ({client.mode})</span>
          <span className="topbar-chip">Type: {state.batchType.toUpperCase()}</span>
        </div>
      </header>

      <section className="kpi-strip section-enter">
        <article className="kpi-card">
          <p className="kpi-label">Queued Files</p>
          <p className="kpi-value">{state.files.length}</p>
        </article>
        <article className="kpi-card">
          <p className="kpi-label">Backend Status</p>
          <div className="mt-1">
            <StatusBadge status={state.batch?.status} />
          </div>
        </article>
      </section>

      <section className="ledger-shell">
        <section className="section-enter ledger-card p-4">
          <div className="grid gap-4 md:grid-cols-[1.1fr_1fr] md:items-end">
            <BatchTypeSelector value={state.batchType} onChange={handleBatchTypeChange} />
            <RunDatePicker value={state.runDate} onChange={actions.setRunDate} />
          </div>
          <p className="mt-2 text-xs text-ledger-smoke">Switching Daily/Office clears currently loaded files.</p>

          {state.batchType === "daily" ? (
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <PdfDropzone
                onFilesAdded={(files) => actions.addFiles(files, "bar")}
                disabled={flags.isBusy}
                title="BAR PDF"
                description="Daily settlement BAR files (multiple files)."
                buttonText="Add PDF"
                allowMultiple
              />
              <PdfDropzone
                onFilesAdded={(files) => actions.addFiles(files, "zbon")}
                disabled={flags.isBusy}
                title="ZBON PDF"
                description="Daily ZBON file (single file only)."
                buttonText="Add PDF"
                allowMultiple={false}
              />
            </div>
          ) : (
            <div className="mt-4">
              <PdfDropzone
                onFilesAdded={(files) => actions.addFiles(files, "office")}
                disabled={flags.isBusy}
                title="OFFICE PDF"
                description="Office invoices/bank statements."
                buttonText="Add PDF"
              />
            </div>
          )}

          {state.rejectedMessage ? (
            <div className="mt-3">
              <AlertBanner tone="error" message={state.rejectedMessage} />
            </div>
          ) : null}

          <div className="mt-4">
            <h2 className="mb-2 text-lg font-semibold">Items to Be Confirmed</h2>
            <FileQueuePanel files={state.files} onRemove={actions.removeFile} />
          </div>

          {state.formError ? (
            <div className="mt-3">
              <AlertBanner tone="error" message={state.formError} />
            </div>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              type="button"
              variant="primary"
              onClick={() => void actions.submitBatch()}
              disabled={!flags.canSubmitBatch || !state.files.length}
            >
              Create Batch
            </Button>
            <Button type="button" variant="ghost" onClick={() => actions.retryPolling()} disabled={!state.batch || flags.isBusy}>
              Retry Status Poll
            </Button>
            <Button type="button" variant="ghost" onClick={() => navigate("/manual-review")} disabled={!canGoReview}>
              Go to Manual Review
            </Button>
          </div>

          {state.batch && !canGoReview ? (
            <div className="mt-3">
              <AlertBanner message={`Batch is ${state.batch.status}. Manual review opens when status reaches review_ready.`} />
            </div>
          ) : null}

          {state.systemError ? <AlertBanner tone="error" message={state.systemError} /> : null}
          {flags.isDone ? <AlertBanner message="Merge finished. Workflow reached done state." /> : null}
        </section>
      </section>
    </AppFrame>
  );
}
