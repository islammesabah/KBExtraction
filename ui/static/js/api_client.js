/**
 * Minimal API client for the UI.
 *
 * We keep all fetch / error-handling patterns here so the UI logic remains clean.
 */

export async function fetchJson(url, options = {}) {
  let resp;
  try {
    resp = await fetch(url, options);
  } catch (err) {
    // AbortController cancellation should not be treated as an error
    if (err?.name === "AbortError") {
      // Return a recognizable "no-op" value; caller can ignore.
      return { aborted: true };
    }
    throw err;
  }

  const data = await resp.json().catch(() => ({}));

  if (!resp.ok) {
    const msg = data?.error || `HTTP ${resp.status} calling ${url}`;
    throw new Error(msg);
  }
  return data;
}