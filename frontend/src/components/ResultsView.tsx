import type { GameResult } from "../types";
import { GameResults } from "./GameResults";

interface ResultsViewProps {
  result: GameResult;
}

export function ResultsView({ result }: ResultsViewProps) {
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
    </div>
  );
}
