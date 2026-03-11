export type PipelineStep =
  | "downloading"
  | "transcribing"
  | "splitting_games"
  | "improving_diarization"
  | "generating_summaries"
  | "done"
  | "failed";

export interface JobStatus {
  job_id: string;
  step: PipelineStep;
  detail: string;
}

export interface PlayerSummary {
  player_name: string;
  role: string | null;
  summary: string;
}

export interface GameSummary {
  game_number: number;
  title: string;
  winner: string;
  summary: string;
  key_moments: string[];
  players: PlayerSummary[];
}

export interface PersonalAdvice {
  player_name: string;
  role: string | null;
  mistakes: string[];
  good_plays: string[];
  advice: string;
}

export interface GameAnalysis {
  summary: GameSummary;
  advice: PersonalAdvice[];
}

export interface JobResult {
  job_id: string;
  games: GameAnalysis[];
  error: string | null;
}
