import { describe, expect, it, vi } from "vitest";
import { createRealUploadClient } from "./uploadClient.real";

describe("uploadClient.real", () => {
  it("calls create batch endpoint with POST", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      text: async () =>
        JSON.stringify({
          schema_version: "v1",
          batch_id: "b-1",
          type: "daily",
          status: "queued",
          run_date: "04/02/2026",
          inputs: [{ path: "a.pdf", category: "bar" }],
          artifacts: {},
          review_rows_count: 0,
          merge_output: {},
          error: null,
          created_at: "2026-02-08T00:00:00Z",
          updated_at: "2026-02-08T00:00:00Z",
        }),
    });

    const client = createRealUploadClient({ baseUrl: "http://127.0.0.1:8000", fetchImpl });
    await client.createBatch({
      type: "daily",
      run_date: "04/02/2026",
      inputs: [{ path: "a.pdf", category: "bar" }],
      metadata: {},
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/batches",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("calls multipart upload endpoint with expected form fields", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      text: async () =>
        JSON.stringify({
          schema_version: "v1",
          task_id: "t-1",
          batch_id: "b-1",
          type: "daily",
          status: "queued",
          created_at: "2026-02-08T00:00:00Z",
        }),
    });

    const client = createRealUploadClient({ baseUrl: "http://127.0.0.1:8000", fetchImpl });
    const zbon = new File(["zbon"], "zbon.pdf", { type: "application/pdf" });
    const bar = new File(["bar"], "bar.pdf", { type: "application/pdf" });

    await client.createBatchUpload({
      files: [
        { file: zbon, category: "zbon", name: "zbon.pdf" },
        { file: bar, category: "bar", name: "bar.pdf" },
      ],
      batchType: "daily",
      runDate: "04/02/2026",
      metadata: {},
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/batches/upload",
      expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
    );
  });

  it("maps 422 style responses to thrown errors", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: async () => JSON.stringify({ detail: "Validation Error" }),
    });

    const client = createRealUploadClient({ baseUrl: "http://127.0.0.1:8000", fetchImpl });

    await expect(
      client.createBatch({
        type: "daily",
        run_date: "04/02/2026",
        inputs: [{ path: "a.pdf", category: "bar" }],
      }),
    ).rejects.toBeTruthy();
  });

  it("fetches review rows payload", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      text: async () =>
        JSON.stringify({
          rows: [{ row_id: "row-0001", category: "bar", filename: "a.pdf", result: {}, score: {} }],
        }),
    });
    const client = createRealUploadClient({ baseUrl: "http://127.0.0.1:8000", fetchImpl });
    const payload = await client.getReviewRows("b-1");
    expect(payload.rows).toHaveLength(1);
  });

  it("uploads local merge source excel", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ monthly_excel_path: "outputs/monthly/current.xlsx" }),
    });
    const client = createRealUploadClient({ baseUrl: "http://127.0.0.1:8000", fetchImpl });
    const file = new File(["xlsx"], "monthly.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

    const payload = await client.uploadMergeSourceLocal("b-1", file);
    expect(payload.monthly_excel_path).toContain("outputs/monthly/current.xlsx");
  });
});
