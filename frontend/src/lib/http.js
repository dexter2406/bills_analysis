/**
 * Error wrapper for HTTP failures.
 */
export class AppHttpError extends Error {
  /**
   * @param {string} message
   * @param {{ status?: number; details?: unknown }} [options]
   */
  constructor(message, options = {}) {
    super(message);
    this.name = "AppHttpError";
    this.status = options.status;
    this.details = options.details;
  }
}

/**
 * Convert unknown failures to user-facing text.
 * @param {unknown} error
 */
export function toErrorMessage(error) {
  if (error instanceof AppHttpError) {
    if (typeof error.details === "object" && error.details && "detail" in error.details) {
      const detail = error.details.detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error.";
}

/**
 * Send a JSON request with timeout support.
 * @param {{
 *  baseUrl: string;
 *  path: string;
 *  method?: string;
 *  body?: unknown;
 *  headers?: Record<string, string>;
 *  timeoutMs?: number;
 *  fetchImpl?: typeof fetch;
 * }} params
 */
export async function requestJson({
  baseUrl,
  path,
  method = "GET",
  body,
  headers = {},
  timeoutMs = 12000,
  fetchImpl = fetch,
}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchImpl(`${baseUrl}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });

    const text = await response.text();
    const payload = text ? safeParseJson(text) : null;

    if (!response.ok) {
      throw new AppHttpError(`Request failed with status ${response.status}.`, {
        status: response.status,
        details: payload,
      });
    }

    return payload;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new AppHttpError("Request timed out.");
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Parse JSON in a safe way while preserving non-JSON payloads.
 * @param {string} value
 */
function safeParseJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}
