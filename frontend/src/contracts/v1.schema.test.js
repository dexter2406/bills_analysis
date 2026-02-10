import { describe, expect, it } from "vitest";
import { parseCreateBatchRequest, parseMergeRequest } from "./v1.schema";

describe("v1 schema contract", () => {
  it("accepts valid create payload", () => {
    const payload = parseCreateBatchRequest({
      type: "daily",
      run_date: "04/02/2026",
      inputs: [{ path: "a.pdf", category: "bar" }],
      metadata: {},
    });

    expect(payload.type).toBe("daily");
    expect(payload.run_date).toBe("04/02/2026");
  });

  it("accepts backward-compatible batch_type alias", () => {
    const payload = parseCreateBatchRequest({
      batch_type: "office",
      run_date: "04/02/2026",
      inputs: [{ path: "a.pdf", category: "office" }],
    });

    expect(payload.type).toBe("office");
  });

  it("rejects invalid run_date", () => {
    expect(() =>
      parseCreateBatchRequest({
        type: "daily",
        run_date: "2026-02-04",
        inputs: [{ path: "a.pdf", category: "bar" }],
      }),
    ).toThrow();
  });

  it("rejects unknown fields", () => {
    expect(() =>
      parseCreateBatchRequest({
        type: "daily",
        run_date: "04/02/2026",
        inputs: [{ path: "a.pdf", category: "bar" }],
        foo: "bar",
      }),
    ).toThrow();
  });

  it("rejects invalid merge mode", () => {
    expect(() => parseMergeRequest({ mode: "upsert" })).toThrow();
  });
});
