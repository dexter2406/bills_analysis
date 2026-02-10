import { API_BASE_URL, API_MODE } from "../../../config/env";
import { createMockUploadClient } from "./uploadClient.mock";
import { createRealUploadClient } from "./uploadClient.real";

/**
 * Create the upload client implementation based on selected API mode.
 * @param {{ mode?: "mock" | "real"; baseUrl?: string; fetchImpl?: typeof fetch }} [options]
 */
export function createUploadClient(options = {}) {
  const mode = options.mode || API_MODE;
  const baseUrl = options.baseUrl || API_BASE_URL;

  if (mode === "real") {
    return createRealUploadClient({ baseUrl, fetchImpl: options.fetchImpl });
  }

  return createMockUploadClient();
}
