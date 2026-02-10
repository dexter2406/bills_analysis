/**
 * Compact alert banner used for error and info notices.
 * @param {{
 *  tone?: "error" | "info";
 *  message: string;
 * }} props
 */
export function AlertBanner({ tone = "info", message }) {
  const toneClass = tone === "error" ? "border-red-200 bg-red-50 text-red-800" : "border-blue-200 bg-blue-50 text-blue-800";

  return <p className={`rounded-md border px-3 py-2 text-sm ${toneClass}`}>{message}</p>;
}
