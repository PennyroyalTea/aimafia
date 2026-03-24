import { useEffect, useState } from "react";
import { listGames, type GameListItem } from "../api/client";

interface GamesListProps {
  onSelect: (gameId: string) => void;
  onBack: () => void;
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "done":
      return "status-badge status-done";
    case "failed":
      return "status-badge status-failed";
    default:
      return "status-badge status-progress";
  }
}

function formatSource(item: GameListItem): string {
  if (!item.video_url) return "(uploaded file)";
  try {
    const url = new URL(item.video_url);
    const path = url.pathname;
    const filename = path.split("/").pop();
    if (filename) return filename;
  } catch {
    // not a valid URL, use as-is
  }
  return item.video_url;
}

export function GamesList({ onSelect, onBack }: GamesListProps) {
  const [games, setGames] = useState<GameListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listGames()
      .then((items) => {
        items.sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setGames(items);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="games-list-loading">Loading games...</div>;
  }

  if (error) {
    return (
      <div className="error-box">
        <h3>Error</h3>
        <pre>{error}</pre>
        <button onClick={onBack}>Go back</button>
      </div>
    );
  }

  return (
    <div className="games-list">
      <div className="games-list-header">
        <h3>All games</h3>
        <button className="games-list-back" onClick={onBack}>
          Back
        </button>
      </div>

      {games.length === 0 ? (
        <p className="games-list-empty">No games yet.</p>
      ) : (
        <table className="games-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Language</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {games.map((g) => (
              <tr
                key={g.game_id}
                className={g.status === "done" ? "games-row-clickable" : ""}
                onClick={() => g.status === "done" && onSelect(g.game_id)}
              >
                <td className="games-source">{formatSource(g)}</td>
                <td>{g.language}</td>
                <td>
                  <span className={statusBadgeClass(g.status)}>{g.status}</span>
                </td>
                <td>{new Date(g.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
