import type { PersonalAdvice } from "../types";

interface PlayerAdviceProps {
  advice: PersonalAdvice;
}

export function PlayerAdviceCard({ advice }: PlayerAdviceProps) {
  return (
    <div className="player-advice">
      <h4>
        {advice.player_name}
        {advice.role && <span className="role"> ({advice.role})</span>}
      </h4>

      {advice.good_plays.length > 0 && (
        <div className="good-plays">
          <h5>Good plays</h5>
          <ul>
            {advice.good_plays.map((play, i) => (
              <li key={i}>{play}</li>
            ))}
          </ul>
        </div>
      )}

      {advice.mistakes.length > 0 && (
        <div className="mistakes">
          <h5>Mistakes</h5>
          <ul>
            {advice.mistakes.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="coaching">
        <h5>Coaching</h5>
        <p>{advice.advice}</p>
      </div>
    </div>
  );
}
