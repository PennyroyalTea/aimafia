export type PipelineStep =
  | "downloading"
  | "transcribing"
  | "improving_diarization"
  | "generating_analysis"
  | "done"
  | "failed";

export interface GameStatus {
  game_id: string;
  step: PipelineStep;
  detail: string;
}

export interface PlayerSummary {
  player_name: string;
  role: string | null;
  summary: string;
}

export interface GameSummary {
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

export interface GameResult {
  game_id: string;
  analysis: GameAnalysis | null;
  error: string | null;
}
