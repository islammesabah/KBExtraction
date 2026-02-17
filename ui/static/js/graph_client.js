import { fetchJson } from "./api_client.js";

export async function getSearchKeywords() {
  return fetchJson("/api/graph/search-keywords");
}

export async function getSubgraph(keyword) {
  const url = `/api/graph/subgraph?keyword=${encodeURIComponent(keyword)}`;
  return fetchJson(url);
}
