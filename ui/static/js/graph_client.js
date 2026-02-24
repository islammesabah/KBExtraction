import { fetchJson } from "./api_client.js";

export async function getSearchKeywords(options = {}) {
  return fetchJson("/api/graph/search-keywords", options);
}

export async function getSubgraph(keyword, options = {}) {
  const url = `/api/graph/subgraph?keyword=${encodeURIComponent(keyword)}`;
  return fetchJson(url, options);
}
