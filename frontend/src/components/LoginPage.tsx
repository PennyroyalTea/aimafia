import { useEffect, useRef } from "react";
import { loginWithGoogle, type AuthUser } from "../api/client";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (
            element: HTMLElement,
            config: { theme: string; size: string; width?: number }
          ) => void;
        };
      };
    };
  }
}

interface LoginPageProps {
  onLogin: (user: AuthUser) => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const buttonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) return;

    function initGsi() {
      if (!window.google || !buttonRef.current) return;

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          try {
            const user = await loginWithGoogle(response.credential);
            onLogin(user);
          } catch (err) {
            console.error("Login failed:", err);
          }
        },
      });

      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        width: 300,
      });
    }

    if (window.google) {
      initGsi();
    } else {
      // GSI script may not have loaded yet -- wait for it
      const interval = setInterval(() => {
        if (window.google) {
          clearInterval(interval);
          initGsi();
        }
      }, 100);
      return () => clearInterval(interval);
    }
  }, [onLogin]);

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Mafia Game Analyzer</h1>
        <p>Sign in to access the analyzer</p>
        <div ref={buttonRef} className="google-btn-container" />
      </div>
    </div>
  );
}
