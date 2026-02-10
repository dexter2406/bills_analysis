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
});
