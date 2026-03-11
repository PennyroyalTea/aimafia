import type { PipelineStep } from "../types";

const STEP_LABELS: Record<PipelineStep, string> = {
  downloading: "Downloading video",
  transcribing: "Transcribing audio",
  splitting_games: "Splitting into games",
  improving_diarization: "Identifying players",
  generating_summaries: "Generating analysis",
  done: "Done",
  failed: "Failed",
};

const STEP_ORDER: PipelineStep[] = [
  "downloading",
  "transcribing",
  "splitting_games",
  "improving_diarization",
  "generating_summaries",
];

interface JobProgressProps {
  currentStep: PipelineStep;
  detail: string;
}

export function JobProgress({ currentStep, detail }: JobProgressProps) {
  const currentIdx = STEP_ORDER.indexOf(currentStep);

  return (
    <div className="job-progress">
      <div className="steps">
        {STEP_ORDER.map((step, idx) => {
          let className = "step";
          if (idx < currentIdx) className += " completed";
          else if (idx === currentIdx) className += " active";

          return (
            <div key={step} className={className}>
              <div className="step-indicator">
                {idx < currentIdx ? (
                  <span className="check">&#10003;</span>
                ) : idx === currentIdx ? (
                  <span className="spinner" />
                ) : (
                  <span className="dot" />
                )}
              </div>
              <span className="step-label">{STEP_LABELS[step]}</span>
            </div>
          );
        })}
      </div>
      {detail && <p className="detail">{detail}</p>}
    </div>
  );
}
