import { useCallback, useRef, useState } from "react";
import "./App.css";
import { submitJob, subscribeToJob } from "./api/client";
import { JobProgress } from "./components/JobProgress";
import { ResultsView } from "./components/ResultsView";
import { UrlInput } from "./components/UrlInput";
import type { JobResult, PipelineStep } from "./types";

type AppState = "idle" | "processing" | "done" | "error";

function App() {
  const [appState, setAppState] = useState<AppState>("idle");
  const [currentStep, setCurrentStep] = useState<PipelineStep>("downloading");
  const [stepDetail, setStepDetail] = useState("");
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string>("");
  const unsubRef = useRef<(() => void) | null>(null);

  const handleSubmit = useCallback(async (url: string, language: string) => {
    setAppState("processing");
    setCurrentStep("downloading");
    setStepDetail("");
    setResult(null);
    setError("");

    try {
      const jobId = await submitJob(url, language);

      const unsub = subscribeToJob(
        jobId,
        (status) => {
          setCurrentStep(status.step);
          setStepDetail(status.detail);
          if (status.step === "failed") {
            setAppState("error");
            setError(status.detail || "Pipeline failed");
          }
        },
        (jobResult) => {
          if (jobResult.error) {
            setAppState("error");
            setError(jobResult.error);
          } else {
            setResult(jobResult);
            setAppState("done");
          }
        },
        (err) => {
          setAppState("error");
          setError(err.message);
        }
      );

      unsubRef.current = unsub;
    } catch (err) {
      setAppState("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const handleReset = () => {
    unsubRef.current?.();
    unsubRef.current = null;
    setAppState("idle");
    setResult(null);
    setError("");
  };

  return (
    <div className="app">
      <h1>Mafia Game Analyzer</h1>
      <p className="subtitle">
        Analyze mafia game videos with AI-powered transcription and coaching
      </p>

      <UrlInput onSubmit={handleSubmit} disabled={appState === "processing"} />

      {appState === "processing" && (
        <JobProgress currentStep={currentStep} detail={stepDetail} />
      )}

      {appState === "error" && (
        <div className="error-box">
          <h3>Error</h3>
          <pre>{error}</pre>
          <button onClick={handleReset}>Try again</button>
        </div>
      )}

      {appState === "done" && result && (
        <>
          <ResultsView result={result} />
          <button className="reset-btn" onClick={handleReset}>
            Analyze another video
          </button>
        </>
      )}
    </div>
  );
}

export default App;
