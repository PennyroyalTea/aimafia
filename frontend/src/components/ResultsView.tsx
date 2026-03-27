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
  const [savingPdf, setSavingPdf] = useState(false);

  const handleSavePdf = async () => {
    if (!result.game_id) return;
    setSavingPdf(true);
    try {
      const res = await fetch(`/api/games/${result.game_id}/pdf`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("PDF generation failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        (result.analysis?.summary.title || "game-analysis") + ".pdf";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setSavingPdf(false);
    }
  };

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
      <button className="print-btn" onClick={handleSavePdf} disabled={savingPdf}>
        {savingPdf ? "Generating PDF..." : "Save as PDF"}
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
