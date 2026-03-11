import { useState } from "react";
import type { JobResult } from "../types";
import { GameResults } from "./GameResults";

interface ResultsViewProps {
  result: JobResult;
}

export function ResultsView({ result }: ResultsViewProps) {
  const [activeGame, setActiveGame] = useState(0);

  if (result.error) {
    return (
      <div className="results-error">
        <h3>Analysis failed</h3>
        <pre>{result.error}</pre>
      </div>
    );
  }

  if (result.games.length === 0) {
    return <p>No games found in the video.</p>;
  }

  return (
    <div className="results-view">
      <button className="print-btn" onClick={() => window.print()}>
        Save as PDF
      </button>
      {result.games.length > 1 && (
        <div className="game-tabs">
          {result.games.map((g, i) => (
            <button
              key={i}
              className={`game-tab ${i === activeGame ? "active" : ""}`}
              onClick={() => setActiveGame(i)}
            >
              {g.summary.title || `Game ${g.summary.game_number}`}
            </button>
          ))}
        </div>
      )}
      <GameResults game={result.games[activeGame]} />
    </div>
  );
}
