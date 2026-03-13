import type { JobResult, JobStatus } from "../types";

const API_BASE = "/api";

export interface UrlMatch {
  job_id: string;
  language: string;
  created_at: string;
  has_transcript: boolean;
  has_result: boolean;
}

export async function checkUrl(
  url: string,
  language: string
): Promise<UrlMatch[]> {
  const res = await fetch(
    `${API_BASE}/check-url?url=${encodeURIComponent(url)}&language=${encodeURIComponent(language)}`
  );
  if (!res.ok) {
    throw new Error(`Failed to check URL: ${res.statusText}`);
  }
  return res.json();
}

export async function submitJob(
  videoUrl: string,
  language: string = "ru",
  mode: string = "full"
): Promise<string> {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_url: videoUrl, language, mode }),
  });
  if (!res.ok) {
    throw new Error(`Failed to submit job: ${res.statusText}`);
  }
  const data = await res.json();
  return data.job_id;
}

export async function getJob(
  jobId: string
): Promise<{ status: JobStatus; result?: JobResult }> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) {
    throw new Error(`Failed to get job: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadFile(
  file: File,
  language: string = "ru"
): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  form.append("language", language);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Failed to upload file: ${res.statusText}`);
  }
  const data = await res.json();
  return data.job_id;
}

export interface InterestSubmission {
  name: string;
  email: string;
  role: string;
  location: string;
  comment: string;
}

export async function submitInterest(
  data: InterestSubmission
): Promise<void> {
  const res = await fetch(`${API_BASE}/interest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to submit interest: ${res.statusText}`);
  }
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
