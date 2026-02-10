import { describe, expect, it, vi } from "vitest";
import { createUploadClient } from "./uploadClient";

describe("createUploadClient", () => {
  it("returns mock client when mode is mock", () => {
    const client = createUploadClient({ mode: "mock" });
    expect(client.mode).toBe("mock");
  });

  it("returns real client when mode is real", () => {
    const fetchImpl = vi.fn();
    const client = createUploadClient({ mode: "real", baseUrl: "http://127.0.0.1:8000", fetchImpl });
    expect(client.mode).toBe("real");
  });
});
