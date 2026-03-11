import type { GameAnalysis } from "../types";
import { PlayerAdviceCard } from "./PlayerAdvice";

interface GameResultsProps {
  game: GameAnalysis;
}

export function GameResults({ game }: GameResultsProps) {
  const { summary } = game;

  return (
    <div className="game-results">
      <div className="game-summary">
        <div className="summary-header">
          <span className={`winner-badge ${summary.winner}`}>
            {summary.winner === "mafia"
              ? "Mafia wins"
              : summary.winner === "citizens"
                ? "Citizens win"
                : "Unknown outcome"}
          </span>
        </div>

        <p className="summary-text">{summary.summary}</p>

        {summary.key_moments.length > 0 && (
          <div className="key-moments">
            <h4>Key moments</h4>
            <ul>
              {summary.key_moments.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          </div>
        )}

        {summary.players.length > 0 && (
          <div className="player-summaries">
            <h4>Players</h4>
            {summary.players.map((p) => (
              <div key={p.player_name} className="player-summary">
                <strong>
                  {p.player_name}
                  {p.role && <span className="role"> ({p.role})</span>}
                </strong>
                <p>{p.summary}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {game.advice.length > 0 && (
        <div className="advice-section">
          <h3>Personal coaching</h3>
          <div className="advice-grid">
            {game.advice.map((a) => (
              <PlayerAdviceCard key={a.player_name} advice={a} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
