/** Always return a plain string from an Axios/FastAPI error.
 *  FastAPI 422 responses return `detail` as an array of objects; rendering that
 *  array directly as a React child throws React error #31 and blanks the page. */
export function extractErrorMessage(err: unknown, fallback = "Something went wrong. Please try again."): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : ""))
      .filter(Boolean);
    if (msgs.length) return msgs.join("; ");
  }
  return fallback;
}
