import type { JobResult, JobStatus } from "../types";

const API_BASE = "/api";

export async function submitJob(
  videoUrl: string,
  language: string = "ru"
): Promise<string> {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_url: videoUrl, language }),
  });
  if (!res.ok) {
    throw new Error(`Failed to submit job: ${res.statusText}`);
  }
  const data = await res.json();
  return data.job_id;
}

export function subscribeToJob(
  jobId: string,
  onStatus: (status: JobStatus) => void,
  onResult: (result: JobResult) => void,
  onError: (error: Error) => void
): () => void {
  const es = new EventSource(`${API_BASE}/jobs/${jobId}/events`);

  es.addEventListener("status", (e) => {
    const status: JobStatus = JSON.parse(e.data);
    onStatus(status);
  });

  es.addEventListener("result", (e) => {
    const result: JobResult = JSON.parse(e.data);
    onResult(result);
    es.close();
  });

  es.onerror = () => {
    onError(new Error("SSE connection lost"));
    es.close();
  };

  return () => es.close();
}
