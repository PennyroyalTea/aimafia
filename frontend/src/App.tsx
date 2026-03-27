import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import {
  checkAuth,
  getGame,
  logout,
  subscribeToGame,
  uploadGameFile,
  type AuthUser,
} from "./api/client";
import { GamesList } from "./components/GamesList";
import { JobProgress } from "./components/JobProgress";
import { LandingPage } from "./components/LandingPage";
import { LoginPage } from "./components/LoginPage";
import { ResultsView } from "./components/ResultsView";
import { UrlInput } from "./components/UrlInput";
import type { GameResult, PipelineStep } from "./types";

type AppState = "idle" | "browsing" | "processing" | "done" | "error";

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

  const handleSubmit = useCallback(
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
  };

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
            disabled={appState === "processing"}
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
            Analyze another game
          </button>
        </>
      )}
    </div>
  );
}

export default App;
