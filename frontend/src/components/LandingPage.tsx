import { useState, type FormEvent } from "react";
import "./LandingPage.css";

export function LandingPage() {
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !contact.trim()) return;

    setSubmitting(true);
    // Simulate submission -- replace with real endpoint later
    await new Promise((r) => setTimeout(r, 600));
    setSubmitted(true);
    setSubmitting(false);
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

        {submitted ? (
          <div className="landing-confirmation">
            <div className="landing-confirmation-mark">&#10003;</div>
            <p className="landing-confirmation-text">
              Got it. We'll reach out when a spot opens up.
            </p>
          </div>
        ) : (
          <form className="landing-form" onSubmit={handleSubmit}>
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
            <div className="landing-field">
              <label className="landing-label" htmlFor="contact">
                Telegram or email
              </label>
              <input
                id="contact"
                className="landing-input"
                type="text"
                value={contact}
                onChange={(e) => setContact(e.target.value)}
                placeholder="@handle or email"
                required
              />
            </div>
            <button
              className="landing-submit"
              type="submit"
              disabled={submitting || !name.trim() || !contact.trim()}
            >
              {submitting ? "Sending..." : "Request access"}
            </button>
          </form>
        )}
      </main>

      <footer className="landing-footer">
        <span className="landing-footer-dot" />
        <span>Moscow</span>
      </footer>
    </div>
  );
}
