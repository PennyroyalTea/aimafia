import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import {
  checkAuth,
  checkUrl,
  createGame,
  getGame,
  logout,
  subscribeToGame,
  uploadGameFile,
  type AuthUser,
  type UrlMatch,
} from "./api/client";
import { GamesList } from "./components/GamesList";
import { JobProgress } from "./components/JobProgress";
import { LandingPage } from "./components/LandingPage";
import { LoginPage } from "./components/LoginPage";
import { ResultsView } from "./components/ResultsView";
import { UrlInput } from "./components/UrlInput";
import type { GameResult, PipelineStep } from "./types";

type AppState = "idle" | "browsing" | "choosing" | "processing" | "done" | "error";

function App() {
  // Show landing page on "/" and analyzer on "/app"
  if (window.location.pathname === "/" || !window.location.pathname.startsWith("/app")) {
    return <LandingPage />;
  }

  return <AuthenticatedApp />;
}

function AuthenticatedApp() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    checkAuth().then((u) => {
      setUser(u);
      setAuthChecked(true);
    });
  }, []);

  const handleLogout = async () => {
    await logout();
    setUser(null);
  };

  if (!authChecked) return null;

  if (!user) {
    return <LoginPage onLogin={setUser} />;
  }

  return <AnalyzerApp user={user} onLogout={handleLogout} />;
}

function AnalyzerApp({ user, onLogout }: { user: AuthUser; onLogout: () => void }) {
  const [appState, setAppState] = useState<AppState>("idle");
  const [currentStep, setCurrentStep] = useState<PipelineStep>("downloading");
  const [stepDetail, setStepDetail] = useState("");
  const [result, setResult] = useState<GameResult | null>(null);
  const [error, setError] = useState<string>("");
  const unsubRef = useRef<(() => void) | null>(null);

  // State for the choice dialog
  const [pendingUrl, setPendingUrl] = useState("");
  const [pendingLanguage, setPendingLanguage] = useState("");
  const [urlMatches, setUrlMatches] = useState<UrlMatch[]>([]);

  const startPipeline = useCallback(
    async (url: string, language: string, mode: string) => {
      setAppState("processing");
      setCurrentStep(mode === "reuse_transcript" ? "improving_diarization" : "downloading");
      setStepDetail("");
      setResult(null);
      setError("");

      try {
        const gameId = await createGame(url, language, mode);

        if (mode === "reuse_result") {
          // Game already completed -- fetch result directly
          const gameData = await getGame(gameId);
          if (gameData.result && !gameData.result.error) {
            setResult(gameData.result);
            setAppState("done");
          } else {
            setAppState("error");
            setError(gameData.result?.error || "No result available");
          }
          return;
        }

        const unsub = subscribeToGame(
          gameId,
          (status) => {
            setCurrentStep(status.step);
            setStepDetail(status.detail);
            if (status.step === "failed") {
              setAppState("error");
              setError(status.detail || "Pipeline failed");
            }
          },
          (gameResult) => {
            if (gameResult.error) {
              setAppState("error");
              setError(gameResult.error);
            } else {
              setResult(gameResult);
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
    },
    []
  );

  const startFileUpload = useCallback(
    async (file: File, language: string) => {
      setAppState("processing");
      setCurrentStep("downloading");
      setStepDetail("Uploading file...");
      setResult(null);
      setError("");

      try {
        const gameId = await uploadGameFile(file, language);

        const unsub = subscribeToGame(
          gameId,
          (status) => {
            setCurrentStep(status.step);
            setStepDetail(status.detail);
            if (status.step === "failed") {
              setAppState("error");
              setError(status.detail || "Pipeline failed");
            }
          },
          (gameResult) => {
            if (gameResult.error) {
              setAppState("error");
              setError(gameResult.error);
            } else {
              setResult(gameResult);
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
    },
    []
  );

  const handleSubmit = useCallback(
    async (url: string, language: string, file?: File) => {
      if (file) {
        startFileUpload(file, language);
        return;
      }

      setResult(null);
      setError("");

      try {
        const matches = await checkUrl(url, language);
        const relevant = matches.filter((m) => m.has_result || m.has_transcript);

        if (relevant.length > 0) {
          setPendingUrl(url);
          setPendingLanguage(language);
          setUrlMatches(relevant);
          setAppState("choosing");
        } else {
          startPipeline(url, language, "full");
        }
      } catch {
        // check-url failed -- just proceed with full run
        startPipeline(url, language, "full");
      }
    },
    [startPipeline, startFileUpload]
  );

  const handleChoice = (mode: string) => {
    setUrlMatches([]);
    startPipeline(pendingUrl, pendingLanguage, mode);
  };

  const handleSelectGame = useCallback(
    async (gameId: string) => {
      setAppState("processing");
      setCurrentStep("downloading");
      setStepDetail("Loading game...");
      setResult(null);
      setError("");

      try {
        const gameData = await getGame(gameId);
        if (gameData.result && !gameData.result.error) {
          setResult(gameData.result);
          setAppState("done");
        } else if (gameData.result?.error) {
          setAppState("error");
          setError(gameData.result.error);
        } else {
          // Still processing -- subscribe to SSE
          const unsub = subscribeToGame(
            gameId,
            (status) => {
              setCurrentStep(status.step);
              setStepDetail(status.detail);
              if (status.step === "failed") {
                setAppState("error");
                setError(status.detail || "Pipeline failed");
              }
            },
            (gameResult) => {
              if (gameResult.error) {
                setAppState("error");
                setError(gameResult.error);
              } else {
                setResult(gameResult);
                setAppState("done");
              }
            },
            (err) => {
              setAppState("error");
              setError(err.message);
            }
          );
          unsubRef.current = unsub;
        }
      } catch (err) {
        setAppState("error");
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    []
  );

  const handleReset = () => {
    unsubRef.current?.();
    unsubRef.current = null;
    setAppState("idle");
    setResult(null);
    setError("");
    setUrlMatches([]);
  };

  const lastProcessed = urlMatches.length > 0 ? urlMatches[0].created_at : "";
  const hasTranscript = urlMatches.some((m) => m.has_transcript);
  const hasResult = urlMatches.some(
    (m) => m.has_result && m.language === pendingLanguage
  );

  return (
    <div className="app">
      <div className="app-header">
        <div>
          <h1>Mafia Game Analyzer</h1>
          <p className="subtitle">
            Analyze mafia game videos with AI-powered transcription and coaching
          </p>
        </div>
        <div className="user-info">
          <span className="user-name">{user.name}</span>
          <button className="logout-btn" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </div>

      {appState !== "browsing" && (
        <>
          <UrlInput
            onSubmit={handleSubmit}
            disabled={appState === "processing" || appState === "choosing"}
          />

          {appState === "idle" && (
            <button
              className="browse-games-link"
              onClick={() => setAppState("browsing")}
            >
              View all games
            </button>
          )}
        </>
      )}

      {appState === "browsing" && (
        <GamesList
          onSelect={handleSelectGame}
          onBack={handleReset}
        />
      )}

      {appState === "choosing" && (
        <div className="choice-dialog">
          <h3>This URL was already processed</h3>
          <p className="choice-detail">
            Last analyzed: {new Date(lastProcessed).toLocaleString()}
          </p>
          <div className="choice-buttons">
            {hasResult && (
              <button
                className="choice-btn choice-reuse-result"
                onClick={() => handleChoice("reuse_result")}
              >
                View previous results
              </button>
            )}
            {hasTranscript && (
              <button
                className="choice-btn choice-reuse-transcript"
                onClick={() => handleChoice("reuse_transcript")}
              >
                Re-analyze (reuse transcript)
              </button>
            )}
            <button
              className="choice-btn choice-full"
              onClick={() => handleChoice("full")}
            >
              Re-analyze from scratch
            </button>
            <button className="choice-btn choice-cancel" onClick={handleReset}>
              Cancel
            </button>
          </div>
        </div>
      )}

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
