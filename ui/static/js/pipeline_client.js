import { fetchJson } from "./api_client.js";

export async function startPipelineJob({ keyword, file }) {
  const form = new FormData();
  form.append("document", file);

  const url = `/api/pipeline/run?keyword=${encodeURIComponent(keyword)}`;
  return fetchJson(url, { method: "POST", body: form });
}

export async function getJobStatus(jobId) {
  return fetchJson(`/api/pipeline/jobs/${encodeURIComponent(jobId)}`);
}
