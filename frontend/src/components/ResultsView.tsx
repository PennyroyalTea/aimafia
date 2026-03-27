import { useState } from "react";
import type { GameResult } from "../types";
import { GameResults } from "./GameResults";

interface ResultsViewProps {
  result: GameResult;
  onReanalyze?: (gameContext: string, model: string) => void;
}

export function ResultsView({ result, onReanalyze }: ResultsViewProps) {
  const [contextOpen, setContextOpen] = useState(false);
  const [gameContext, setGameContext] = useState("");
  const [model, setModel] = useState("claude-sonnet-4-6");

  if (result.error) {
    return (
      <div className="results-error">
        <h3>Analysis failed</h3>
        <pre>{result.error}</pre>
      </div>
    );
  }

  if (!result.analysis) {
    return <p>No analysis available.</p>;
  }

  return (
    <div className="results-view">
      <button className="print-btn" onClick={() => window.print()}>
        Save as PDF
      </button>
      <GameResults game={result.analysis} />
      {onReanalyze && (
        <div className="reanalyze-section">
          <button
            type="button"
            className="context-toggle"
            onClick={() => setContextOpen(!contextOpen)}
          >
            {contextOpen ? "Hide" : "Re-analyze with context"}
          </button>
          {contextOpen && (
            <>
              <textarea
                className="context-textarea"
                placeholder="Paste game moves, kills, voting results, role reveals, or any other context to improve the analysis..."
                value={gameContext}
                onChange={(e) => setGameContext(e.target.value)}
                rows={4}
              />
              <div className="reanalyze-controls">
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                >
                  <option value="claude-sonnet-4-6">Sonnet 4.6</option>
                  <option value="claude-opus-4-6">Opus 4.6</option>
                </select>
                <button
                  className="reanalyze-btn"
                  onClick={() => onReanalyze(gameContext, model)}
                  disabled={!gameContext.trim()}
                >
                  Re-analyze
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
