import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  getAuthConfig,
  loginWithGoogle,
  submitInterest,
  type AuthUser,
} from "../api/client";
import "./LandingPage.css";

type Step = "name" | "details" | "done";

interface LandingPageProps {
  user: AuthUser | null;
  onLogin: (user: AuthUser) => void;
}

export function LandingPage({ user, onLogin }: LandingPageProps) {
  // Interest form state
  const [step, setStep] = useState<Step>("name");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("player");
  const [location, setLocation] = useState("");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Auth state
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const googleBtnRef = useRef<HTMLDivElement>(null);
  const [clientId, setClientId] = useState("");

  useEffect(() => {
    getAuthConfig().then((c) => setClientId(c.google_client_id));
  }, []);

  useEffect(() => {
    if (!clientId || !googleBtnRef.current) return;
    if (user?.authenticated) return;

    google.accounts.id.initialize({
      client_id: clientId,
      callback: async (response) => {
        setAuthLoading(true);
        setAuthError("");
        try {
          const authUser = await loginWithGoogle(response.credential);
          onLogin(authUser);
          window.location.href = "/app";
        } catch (err) {
          setAuthError(
            err instanceof Error ? err.message : "Sign-in failed"
          );
        } finally {
          setAuthLoading(false);
        }
      },
    });

    google.accounts.id.renderButton(googleBtnRef.current, {
      type: "standard",
      theme: "filled_black",
      size: "large",
      text: "signin_with",
      shape: "rectangular",
    });
  }, [clientId, user, onLogin]);

  const handleNameSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setStep("details");
  };

  const handleDetailsSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !location.trim()) return;

    setSubmitting(true);
    setFormError("");
    try {
      await submitInterest({ name, email, role, location, comment });
      setStep("done");
    } catch {
      setFormError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="landing">
      <div className="landing-noise" />

      <main className="landing-main">
        <div className="landing-badge">invite only</div>

        <h1 className="landing-title">
          <span className="landing-title-line">Mafia</span>
          <span className="landing-title-line landing-title-accent">Club</span>
        </h1>

        <p className="landing-description">
          We play mafia and use AI to analyse our games.
        </p>

        <div className="landing-divider" />

        {/* Sign in section */}
        {user?.authenticated ? (
          <div className="landing-signed-in">
            <p className="landing-signed-in-text">
              Signed in as {user.email}
            </p>
            <a href="/app" className="landing-submit">
              Go to analyzer
            </a>
          </div>
        ) : (
          <div className="landing-signin">
            <h2 className="landing-form-heading">Sign in</h2>
            <div ref={googleBtnRef} className="landing-google-btn" />
            {authLoading && (
              <p className="landing-loading">Verifying...</p>
            )}
            {authError && <p className="landing-error">{authError}</p>}
          </div>
        )}

        <div className="landing-divider" style={{ marginTop: "2.5rem" }} />

        {/* Interest form -- always visible for non-members */}
        {step === "done" ? (
          <div className="landing-confirmation">
            <div className="landing-confirmation-mark">&#10003;</div>
            <p className="landing-confirmation-text">
              Got it. We'll reach out when a spot opens up.
            </p>
          </div>
        ) : step === "name" ? (
          <form className="landing-form" onSubmit={handleNameSubmit}>
            <h2 className="landing-form-heading">Express interest</h2>
            <div className="landing-field">
              <label className="landing-label" htmlFor="name">
                Name
              </label>
              <input
                id="name"
                className="landing-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                required
                autoComplete="name"
              />
            </div>
            <button
              className="landing-submit"
              type="submit"
              disabled={!name.trim()}
            >
              Request access
            </button>
          </form>
        ) : (
          <form className="landing-form" onSubmit={handleDetailsSubmit}>
            <h2 className="landing-form-heading">A few more details</h2>
            <div className="landing-field">
              <label className="landing-label" htmlFor="detail-name">
                Name
              </label>
              <input
                id="detail-name"
                className="landing-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                required
                autoComplete="name"
              />
            </div>
            <div className="landing-field">
              <label className="landing-label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                className="landing-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
              />
            </div>
            <div className="landing-field">
              <label className="landing-label">I want to</label>
              <div className="landing-radio-group">
                <label className="landing-radio">
                  <input
                    type="radio"
                    name="role"
                    value="player"
                    checked={role === "player"}
                    onChange={(e) => setRole(e.target.value)}
                  />
                  <span className="landing-radio-label">Play</span>
                </label>
                <label className="landing-radio">
                  <input
                    type="radio"
                    name="role"
                    value="organiser"
                    checked={role === "organiser"}
                    onChange={(e) => setRole(e.target.value)}
                  />
                  <span className="landing-radio-label">Organise</span>
                </label>
                <label className="landing-radio">
                  <input
                    type="radio"
                    name="role"
                    value="both"
                    checked={role === "both"}
                    onChange={(e) => setRole(e.target.value)}
                  />
                  <span className="landing-radio-label">Both</span>
                </label>
              </div>
            </div>
            <div className="landing-field">
              <label className="landing-label" htmlFor="location">
                Location
              </label>
              <input
                id="location"
                className="landing-input"
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="City"
                required
                autoComplete="address-level2"
              />
            </div>
            <div className="landing-field">
              <label className="landing-label" htmlFor="comment">
                Anything else?
              </label>
              <textarea
                id="comment"
                className="landing-input landing-textarea"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Optional"
                rows={3}
              />
            </div>
            {formError && <p className="landing-error">{formError}</p>}
            <button
              className="landing-submit"
              type="submit"
              disabled={submitting || !email.trim() || !location.trim()}
            >
              {submitting ? "Sending..." : "Submit"}
            </button>
          </form>
        )}
      </main>
    </div>
  );
}
