import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppFrame } from "../../../app/AppFrame";
import { AlertBanner } from "../../../shared/ui/AlertBanner";
import { Button } from "../../../shared/ui/Button";
import { StatusBadge } from "../components/StatusBadge";
import { ReviewCategoryTable } from "../components/ReviewCategoryTable";
import { useUploadFlowContext } from "../state/UploadFlowContext";

const DEFAULT_MONTHLY_EXCEL_PATH = "outputs/monthly/current.xlsx";
const SOURCE_LOCAL_FILE = "local_file";
const SOURCE_LARK_SHEET = "lark_sheet";

const barColumns = [
  { key: "filename", label: "File", readOnly: true },
  { key: "store_name", label: "Store Name" },
  { key: "brutto", label: "Brutto" },
  { key: "netto", label: "Netto" },
  { key: "run_date", label: "Run Date" },
];

const zbonColumns = [
  { key: "filename", label: "File", readOnly: true },
  { key: "brutto", label: "Brutto" },
  { key: "netto", label: "Netto" },
  { key: "run_date", label: "Run Date" },
];

const officeColumns = [
  { key: "filename", label: "File", readOnly: true },
  { key: "sender", label: "Sender" },
  { key: "brutto", label: "Brutto" },
  { key: "netto", label: "Netto" },
  { key: "tax_id", label: "Tax ID" },
  { key: "receiver", label: "Receiver" },
];

/**
 * Manual review page for editing row-level fields and controlling merge actions.
 */
export function ManualReviewPage() {
  const navigate = useNavigate();
  const { client, state, actions, flags } = useUploadFlowContext();
  const effectiveBatchType = state.batch?.type || state.batchType || "daily";

  const [draft, setDraft] = useState(() => buildDraftRows(state.files, state.runDate, null));
  const [localError, setLocalError] = useState("");
  const [monthlyPathSource, setMonthlyPathSource] = useState(SOURCE_LOCAL_FILE);
  const [selectedLocalFileName, setSelectedLocalFileName] = useState(null);
  const [larkSheetLink, setLarkSheetLink] = useState("");
  const [mergeMode, setMergeMode] = useState("overwrite");
  const [monthlyPath, setMonthlyPath] = useState(state.mergeRequestPayload?.monthly_excel_path || DEFAULT_MONTHLY_EXCEL_PATH);

  useEffect(() => {
    setDraft((previous) => buildDraftRows(state.files, state.runDate, previous));
  }, [state.files, state.runDate]);

  useEffect(() => {
    const nextMode = effectiveBatchType === "daily" ? "overwrite" : state.mergeRequestPayload?.mode || "overwrite";
    setMergeMode(nextMode);
    setMonthlyPath(state.mergeRequestPayload?.monthly_excel_path || DEFAULT_MONTHLY_EXCEL_PATH);
  }, [effectiveBatchType, state.mergeRequestPayload?.mode, state.mergeRequestPayload?.monthly_excel_path]);

  const onChangeCell = useCallback((section, rowId, key, value) => {
    setDraft((previous) => ({
      ...previous,
      [section]: previous[section].map((row) => (row.id === rowId ? { ...row, [key]: value } : row)),
    }));
  }, []);

  const totalRows = useMemo(
    () => draft.bar.length + draft.zbon.length + draft.office.length,
    [draft.bar.length, draft.office.length, draft.zbon.length],
  );

  const hasBatch = Boolean(state.batch?.batch_id);
  const hasSubmittedReview = state.reviewSubmitted || (state.batch?.review_rows_count || 0) > 0;
  const submitDisabled = !hasBatch || state.batch?.status !== "review_ready" || flags.isBusy || !totalRows || !monthlyPath.trim();
  const showRetryMerge = state.batch?.status === "failed" && hasSubmittedReview;

  const onSubmit = useCallback(async () => {
    setLocalError("");

    if (!monthlyPath.trim()) {
      setLocalError("Monthly Excel Path is required.");
      return;
    }

    if (monthlyPathSource === SOURCE_LARK_SHEET && !isValidHttpUrl(larkSheetLink)) {
      setLocalError("Please enter a valid Lark sheet URL.");
      return;
    }

    const rows = composeReviewRows(draft);
    if (!rows.length) {
      setLocalError("No review rows available.");
      return;
    }

    const reviewOk = await actions.submitReviewOnly(rows);
    if (!reviewOk) {
      setLocalError("Review submission failed. Please check system error and retry.");
      return;
    }

    const mergeOk = await actions.queueMergeOnly({
      mode: effectiveBatchType === "daily" ? "overwrite" : mergeMode,
      monthly_excel_path: monthlyPath.trim(),
      metadata: monthlyPathSource === SOURCE_LARK_SHEET ? { lark_sheet_link: larkSheetLink.trim() } : {},
    });
    if (!mergeOk) {
      setLocalError("Review saved, but merge queue failed. Please retry.");
    }
  }, [actions, draft, effectiveBatchType, larkSheetLink, mergeMode, monthlyPath, monthlyPathSource]);

  const onRetryMerge = useCallback(async () => {
    setLocalError("");
    const ok = await actions.retryMerge();
    if (!ok) {
      setLocalError("Retry merge failed. Batch must be in failed state with submitted review rows.");
    }
  }, [actions]);

  const onSelectLocalExcel = useCallback((event) => {
    const selected = event.target.files?.[0];
    if (!selected) {
      return;
    }
    setSelectedLocalFileName(selected.name);
    setMonthlyPath(`local://${selected.name}`);
    setMonthlyPathSource(SOURCE_LOCAL_FILE);
  }, []);

  return (
    <AppFrame>
      <header className="app-topbar section-enter">
        <div>
          <h1>Manual Review</h1>
          <p>Edit extracted fields by category, then submit results in one step.</p>
        </div>
        <div className="topbar-meta">
          <span className="topbar-chip success">API Connected: v1 ({client.mode})</span>
          <StatusBadge status={state.batch?.status} />
        </div>
      </header>

      <section className="kpi-strip section-enter">
        <article className="kpi-card">
          <p className="kpi-label">Current Batch</p>
          <p className="kpi-value">{state.batch?.batch_id || "--"}</p>
        </article>
        <article className="kpi-card">
          <p className="kpi-label">Rows</p>
          <p className="kpi-value">{totalRows}</p>
        </article>
        <article className="kpi-card">
          <p className="kpi-label">Review Rows Count</p>
          <p className="kpi-value">{state.batch?.review_rows_count ?? 0}</p>
        </article>
      </section>

      <section className="ledger-shell space-y-4">
        {!state.batch ? <AlertBanner tone="error" message="No batch found. Create a batch from Upload Management first." /> : null}
        {state.batch && state.batch.status !== "review_ready" ? (
          <AlertBanner message={`Batch is ${state.batch.status}. Submit is enabled only when status is review_ready.`} />
        ) : null}

        <ReviewCategoryTable
          title="BAR Review Items"
          description="Daily BAR receipts: store name and amount verification."
          rows={draft.bar}
          columns={barColumns}
          onChangeCell={(rowId, key, value) => onChangeCell("bar", rowId, key, value)}
        />

        <ReviewCategoryTable
          title="ZBON Review Items"
          description="Daily ZBON summary: amount and date verification."
          rows={draft.zbon}
          columns={zbonColumns}
          onChangeCell={(rowId, key, value) => onChangeCell("zbon", rowId, key, value)}
        />

        <ReviewCategoryTable
          title="OFFICE Review Items"
          description="Office invoices: sender/tax metadata and amount verification."
          rows={draft.office}
          columns={officeColumns}
          onChangeCell={(rowId, key, value) => onChangeCell("office", rowId, key, value)}
        />

        <section className="ledger-card p-4">
          <header className="mb-3">
            <h3 className="text-lg font-semibold">Confirm Results</h3>
            <p className="mt-1 text-xs text-ledger-smoke">After finishing review edits, submit once to save review and queue merge.</p>
          </header>

          <div className="source-switch">
            <button
              type="button"
              className={`source-switch-btn ${monthlyPathSource === SOURCE_LOCAL_FILE ? "active" : ""}`}
              onClick={() => setMonthlyPathSource(SOURCE_LOCAL_FILE)}
            >
              from Local
            </button>
            <button
              type="button"
              className={`source-switch-btn ${monthlyPathSource === SOURCE_LARK_SHEET ? "active" : ""}`}
              onClick={() => setMonthlyPathSource(SOURCE_LARK_SHEET)}
            >
              from Lark
            </button>
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm text-ledger-smoke">
              <span className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-ledger-ink">Mode</span>
              <select
                className="review-cell-input"
                value={effectiveBatchType === "daily" ? "overwrite" : mergeMode}
                onChange={(event) => setMergeMode(event.target.value)}
                disabled={effectiveBatchType === "daily"}
              >
                <option value="overwrite">overwrite</option>
                {effectiveBatchType === "office" ? <option value="append">append</option> : null}
              </select>
              {effectiveBatchType === "daily" ? <span className="text-xs">Daily mode uses overwrite only.</span> : null}
            </label>

            <label className="flex flex-col gap-1 text-sm text-ledger-smoke">
              <span className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-ledger-ink">Monthly Excel Path</span>
              <input
                type="text"
                className="review-cell-input"
                placeholder={DEFAULT_MONTHLY_EXCEL_PATH}
                value={monthlyPath}
                onChange={(event) => setMonthlyPath(event.target.value)}
              />
            </label>
          </div>

          {monthlyPathSource === SOURCE_LOCAL_FILE ? (
            <div className="mt-3">
              <label className="flex flex-col gap-1 text-sm text-ledger-smoke">
                <span className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-ledger-ink">Choose Local Excel</span>
                <input type="file" accept=".xlsx,.xls" onChange={onSelectLocalExcel} />
                {selectedLocalFileName ? <span className="text-xs text-ledger-smoke">Selected: {selectedLocalFileName}</span> : null}
              </label>
            </div>
          ) : null}

          {monthlyPathSource === SOURCE_LARK_SHEET ? (
            <div className="mt-3">
              <label className="flex flex-col gap-1 text-sm text-ledger-smoke">
                <span className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-ledger-ink">Lark Sheet Link</span>
                <input
                  type="text"
                  className="review-cell-input"
                  placeholder="https://*.larksuite.com/sheets/..."
                  value={larkSheetLink}
                  onChange={(event) => setLarkSheetLink(event.target.value)}
                />
                <span className="text-xs text-ledger-smoke">Coming Soon: full Lark source integration will be enabled with backend support.</span>
              </label>
            </div>
          ) : null}

          <div className="mt-3 flex flex-wrap gap-2">
            <Button type="button" variant="primary" onClick={() => void onSubmit()} disabled={submitDisabled}>
              Submit
            </Button>
            <Button type="button" variant="ghost" onClick={() => navigate("/")}>
              Back to Upload
            </Button>
            {showRetryMerge ? (
              <Button type="button" variant="danger" onClick={() => void onRetryMerge()} disabled={flags.isBusy}>
                Retry Merge
              </Button>
            ) : null}
          </div>
        </section>

        {localError ? <AlertBanner tone="error" message={localError} /> : null}
        {state.systemError ? <AlertBanner tone="error" message={state.systemError} /> : null}
        {flags.isDone ? <AlertBanner message="Merge finished. Workflow reached done state." /> : null}
      </section>
    </AppFrame>
  );
}

/**
 * Build editable rows for each category while preserving existing edits.
 * @param {Array<{ id: string; name: string; category: "bar" | "zbon" | "office" | null }>} files
 * @param {string} runDate
 * @param {{ bar: Array<Record<string, string>>; zbon: Array<Record<string, string>>; office: Array<Record<string, string>> } | null} previous
 */
function buildDraftRows(files, runDate, previous) {
  const previousMap = new Map();

  if (previous) {
    for (const section of ["bar", "zbon", "office"]) {
      for (const row of previous[section]) {
        previousMap.set(row.id, row);
      }
    }
  }

  const draft = { bar: [], zbon: [], office: [] };

  for (const file of files) {
    if (file.category === "bar") {
      const current = previousMap.get(file.id);
      draft.bar.push({
        id: file.id,
        category: "bar",
        filename: file.name,
        store_name: current?.store_name ?? "-",
        brutto: current?.brutto ?? "-",
        netto: current?.netto ?? "-",
        run_date: current?.run_date ?? runDate ?? "-",
      });
      continue;
    }

    if (file.category === "zbon") {
      const current = previousMap.get(file.id);
      draft.zbon.push({
        id: file.id,
        category: "zbon",
        filename: file.name,
        brutto: current?.brutto ?? "-",
        netto: current?.netto ?? "-",
        run_date: current?.run_date ?? runDate ?? "-",
      });
      continue;
    }

    if (file.category === "office") {
      const current = previousMap.get(file.id);
      draft.office.push({
        id: file.id,
        category: "office",
        filename: file.name,
        sender: current?.sender ?? "-",
        brutto: current?.brutto ?? "-",
        netto: current?.netto ?? "-",
        tax_id: current?.tax_id ?? "-",
        receiver: current?.receiver ?? "-",
      });
    }
  }

  return draft;
}

/**
 * Convert local draft tables into API review rows payload.
 * @param {{ bar: Array<Record<string, string>>; zbon: Array<Record<string, string>>; office: Array<Record<string, string>> }} draft
 */
function composeReviewRows(draft) {
  return [...draft.bar, ...draft.zbon, ...draft.office].map((row) => ({
    ...row,
  }));
}

/**
 * Basic URL validation for scaffold-level lark link input.
 * @param {string} value
 */
function isValidHttpUrl(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}
