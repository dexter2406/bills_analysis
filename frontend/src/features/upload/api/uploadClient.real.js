import { requestJson } from "../../../lib/http";
import {
  parseBatchListResponse,
  parseBatchResponse,
  parseCreateBatchRequest,
  parseMergeRequest,
  parseMergeTaskResponse,
  parseSubmitReviewRequest,
} from "../../../contracts/v1.schema";

/**
 * Build a real upload client wired to backend /v1 endpoints.
 * @param {{ baseUrl: string; fetchImpl?: typeof fetch }} params
 */
export function createRealUploadClient({ baseUrl, fetchImpl }) {
  return {
    mode: "real",

    /**
     * Placeholder upload bridge until multipart endpoint is available.
     * @param {File[]} files
     * @param {{ batchType: "daily" | "office" }} context
     */
    async uploadFiles(files, context) {
      const defaultCategory = context.batchType === "daily" ? "bar" : "office";
      return files.map((file) => ({
        path: `/virtual-upload/${Date.now()}-${safeName(file.name)}`,
        category: defaultCategory,
      }));
    },

    /**
     * @param {unknown} payload
     */
    async createBatch(payload) {
      const body = parseCreateBatchRequest(payload);
      const data = await requestJson({
        baseUrl,
        path: "/v1/batches",
        method: "POST",
        body,
        fetchImpl,
      });
      return parseBatchResponse(data);
    },

    /**
     * @param {string} batchId
     */
    async getBatch(batchId) {
      const data = await requestJson({
        baseUrl,
        path: `/v1/batches/${batchId}`,
        method: "GET",
        fetchImpl,
      });
      return parseBatchResponse(data);
    },

    /**
     * @param {number} [limit]
     */
    async listBatches(limit = 100) {
      const data = await requestJson({
        baseUrl,
        path: `/v1/batches?limit=${limit}`,
        method: "GET",
        fetchImpl,
      });
      return parseBatchListResponse(data);
    },

    /**
     * @param {string} batchId
     * @param {unknown} payload
     */
    async submitReview(batchId, payload) {
      const body = parseSubmitReviewRequest(payload);
      const data = await requestJson({
        baseUrl,
        path: `/v1/batches/${batchId}/review`,
        method: "PUT",
        body,
        fetchImpl,
      });
      return parseBatchResponse(data);
    },

    /**
     * @param {string} batchId
     * @param {unknown} payload
     */
    async queueMerge(batchId, payload) {
      const body = parseMergeRequest(payload);
      const data = await requestJson({
        baseUrl,
        path: `/v1/batches/${batchId}/merge`,
        method: "POST",
        body,
        fetchImpl,
      });
      return parseMergeTaskResponse(data);
    },
  };
}

/**
 * Sanitize file names for virtual upload paths.
 * @param {string} value
 */
function safeName(value) {
  return value.replace(/[^a-zA-Z0-9._-]/g, "_");
}
