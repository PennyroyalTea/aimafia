import type { GameResult, GameStatus } from "../types";

const API_BASE = "/api";

export interface UrlMatch {
  game_id: string;
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

export async function createGame(
  videoUrl: string,
  language: string = "ru",
  mode: string = "full"
): Promise<string> {
  const res = await fetch(`${API_BASE}/games`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_url: videoUrl, language, mode }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create game: ${res.statusText}`);
  }
  const data = await res.json();
  return data.game_id;
}

export async function getGame(
  gameId: string
): Promise<{ status: GameStatus; result?: GameResult }> {
  const res = await fetch(`${API_BASE}/games/${gameId}`);
  if (!res.ok) {
    throw new Error(`Failed to get game: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadGameFile(
  file: File,
  language: string = "ru"
): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  form.append("language", language);
  const res = await fetch(`${API_BASE}/games/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Failed to upload file: ${res.statusText}`);
  }
  const data = await res.json();
  return data.game_id;
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

export function subscribeToGame(
  gameId: string,
  onStatus: (status: GameStatus) => void,
  onResult: (result: GameResult) => void,
  onError: (error: Error) => void
): () => void {
  const es = new EventSource(`${API_BASE}/games/${gameId}/events`);

  es.addEventListener("status", (e) => {
    const status: GameStatus = JSON.parse(e.data);
    onStatus(status);
  });

  es.addEventListener("result", (e) => {
    const result: GameResult = JSON.parse(e.data);
    onResult(result);
    es.close();
  });

  es.onerror = () => {
    onError(new Error("SSE connection lost"));
    es.close();
  };

  return () => es.close();
}
