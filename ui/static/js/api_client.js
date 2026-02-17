/**
 * Minimal API client for the UI.
 *
 * We keep all fetch / error-handling patterns here so the UI logic remains clean.
 */

export async function fetchJson(url, options = {}) {
  const resp = await fetch(url, options);
  const data = await resp.json().catch(() => ({}));

  if (!resp.ok) {
    const msg = data?.error || `HTTP ${resp.status} calling ${url}`;
    throw new Error(msg);
  }
  return data;
}
