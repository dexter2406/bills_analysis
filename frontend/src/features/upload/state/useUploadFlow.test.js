import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createMockUploadClient } from "../api/uploadClient.mock";
import { useUploadFlow } from "./useUploadFlow";

describe("useUploadFlow", () => {
  it("rejects non-PDF files during addFiles", () => {
    const client = createMockUploadClient({ latencyMs: 0 });
    const { result } = renderHook(() => useUploadFlow({ client }));

    const txt = new File(["x"], "notes.txt", { type: "text/plain" });
    result.current.actions.addFiles([txt]);

    expect(result.current.state.files).toHaveLength(0);
    expect(result.current.state.rejectedMessage).toMatch(/Ignored non-PDF files/i);
  });

  it("accepts only one ZBON file", () => {
    const client = createMockUploadClient({ latencyMs: 0 });
    const { result } = renderHook(() => useUploadFlow({ client }));

    const first = new File(["a"], "zbon-1.pdf", { type: "application/pdf" });
    const second = new File(["b"], "zbon-2.pdf", { type: "application/pdf" });

    result.current.actions.addFiles([first], "zbon");
    result.current.actions.addFiles([second], "zbon");

    const zbonFiles = result.current.state.files.filter((file) => file.category === "zbon");
    expect(zbonFiles).toHaveLength(1);
    expect(result.current.state.rejectedMessage).toMatch(/ZBON allows only one file/i);
  });

  it("submits review only without auto-merging", async () => {
    const client = createMockUploadClient({ latencyMs: 0 });
    const { result } = renderHook(() => useUploadFlow({ client }));

    const file = new File(["a"], "invoice.pdf", { type: "application/pdf" });
    result.current.actions.addFiles([file], "bar");
    await result.current.actions.submitBatch();

    await waitFor(() => {
      expect(result.current.state.phase).toBe("review_ready");
    });

    const ok = await result.current.actions.submitReviewOnly([{ filename: "invoice.pdf", brutto: "10.5" }]);
    expect(ok).toBe(true);
    expect(result.current.state.phase).toBe("review_ready");
    expect(result.current.state.reviewSubmitted).toBe(true);
    expect(result.current.state.mergeRequested).toBe(false);
  });

  it("queues merge only after review and reaches done", async () => {
    const client = createMockUploadClient({ latencyMs: 0 });
    const { result } = renderHook(() => useUploadFlow({ client }));

    const file = new File(["a"], "invoice.pdf", { type: "application/pdf" });
    result.current.actions.addFiles([file], "bar");
    await result.current.actions.submitBatch();

    await waitFor(() => {
      expect(result.current.state.phase).toBe("review_ready");
    });

    await result.current.actions.submitReviewOnly([{ filename: "invoice.pdf", brutto: "10.5" }]);
    const mergeOk = await result.current.actions.queueMergeOnly({ mode: "overwrite", monthly_excel_path: null });
    expect(mergeOk).toBe(true);

    await waitFor(() => {
      expect(result.current.state.phase).toBe("done");
    });
  });

  it("blocks retry merge when batch is not failed", async () => {
    const client = createMockUploadClient({ latencyMs: 0 });
    const { result } = renderHook(() => useUploadFlow({ client }));

    const file = new File(["a"], "invoice.pdf", { type: "application/pdf" });
    result.current.actions.addFiles([file], "bar");
    await result.current.actions.submitBatch();

    await waitFor(() => {
      expect(result.current.state.phase).toBe("review_ready");
    });

    const ok = await result.current.actions.retryMerge();
    expect(ok).toBe(false);
    expect(result.current.state.systemError).toMatch(/failed/i);
  });
});
