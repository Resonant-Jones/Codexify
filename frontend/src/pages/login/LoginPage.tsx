import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { useAuth } from "@/components/auth/useAuth";
import { Button } from "@/components/ui/button";
import { getRuntimeConfigSync } from "@/lib/runtimeConfig";

import "./LoginPage.css";

const LOGIN_FAILURE_MESSAGE =
  "Unable to sign in. Check your credentials and try again.";

export default function LoginPage() {
  const auth = useAuth();
  const remoteAuthMode = getRuntimeConfigSync().authMode === "remote";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [logoutLoading, setLogoutLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const usernameInputRef = useRef<HTMLInputElement>(null);
  const wasAuthenticatedRef = useRef(false);

  const canSubmit = username.trim().length > 0 && password.length > 0;
  const activeSession = auth.ready && auth.isAuthenticated;
  const showRegistration = import.meta.env.VITE_PRIVATE_PREVIEW !== "true";

  useEffect(() => {
    if (
      wasAuthenticatedRef.current &&
      auth.ready &&
      !auth.isAuthenticated
    ) {
      usernameInputRef.current?.focus();
    }
    wasAuthenticatedRef.current = activeSession;
  }, [activeSession, auth.isAuthenticated, auth.ready]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || loading) return;
    setLoading(true);
    setError(null);
    try {
      await auth.login({
        username: username.trim(),
        password,
      });
      window.location.assign("/");
    } catch {
      setError(LOGIN_FAILURE_MESSAGE);
    } finally {
      setLoading(false);
    }
  }

  async function handleSwitchUser() {
    if (logoutLoading) return;
    setLogoutLoading(true);
    try {
      await auth.logout();
    } catch {
      // useAuth.logout clears the stored session token in its finally block.
    } finally {
      setLogoutLoading(false);
    }
  }

  const eyebrow = !auth.ready
    ? "LOCAL WORKSPACE"
    : remoteAuthMode
      ? "PRIVATE WORKSPACE"
      : "LOCAL WORKSPACE";
  const heading = !auth.ready
    ? "Preparing your workspace"
    : activeSession
      ? "Your workspace is ready"
      : "Welcome back to Codexify";
  const body = !auth.ready
    ? "Checking the local access state on this device."
    : activeSession
      ? auth.token
        ? "An active session was found on this device."
        : "Local workspace access is already configured on this device."
      : remoteAuthMode
        ? "Sign in to enter your Codexify workspace. This browser will receive a private session token for the active session."
        : "Sign in to enter your local workspace. Your session and workspace data remain on this device.";

  return (
    <main className="login-threshold">
      <div className="login-threshold__atmosphere" aria-hidden="true" />

      <section
        className="login-threshold__composition"
        aria-labelledby="login-threshold-heading"
      >
        <p className="login-threshold__brand">CODEXIFY</p>

        <div className="login-threshold__card">
          <header className="login-threshold__header">
            <p className="login-threshold__eyebrow">{eyebrow}</p>
            <h1
              className="login-threshold__heading"
              id="login-threshold-heading"
            >
              {heading}
            </h1>
            <p className="login-threshold__body">{body}</p>
          </header>

          {!auth.ready ? (
            <div
              className="login-threshold__readiness"
              aria-label="Checking workspace access"
            >
              <span className="login-threshold__readiness-bar" />
            </div>
          ) : activeSession ? (
            <div className="login-threshold__actions">
              <Button
                className="login-threshold__primary-action"
                onClick={() => window.location.assign("/")}
                size="lg"
                type="button"
              >
                CONTINUE TO WORKSPACE
              </Button>

              {auth.token ? (
                <Button
                  className="login-threshold__secondary-action"
                  disabled={logoutLoading}
                  onClick={handleSwitchUser}
                  size="lg"
                  type="button"
                  variant="ghost"
                >
                  {logoutLoading ? "Signing out…" : "Sign in as another user"}
                </Button>
              ) : null}
            </div>
          ) : (
            <>
              <form className="login-threshold__form" onSubmit={handleSubmit}>
                <div className="login-threshold__field">
                  <label htmlFor="login-username">Username</label>
                  <input
                    autoComplete="username"
                    id="login-username"
                    onChange={(event) => setUsername(event.target.value)}
                    placeholder="Enter your username"
                    ref={usernameInputRef}
                    required
                    value={username}
                  />
                </div>

                <div className="login-threshold__field">
                  <label htmlFor="login-password">Password</label>
                  <input
                    aria-describedby={error ? "login-failure" : undefined}
                    aria-invalid={error ? "true" : undefined}
                    autoComplete="current-password"
                    id="login-password"
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Enter your password"
                    required
                    type="password"
                    value={password}
                  />
                </div>

                {error ? (
                  <div
                    className="login-threshold__error"
                    id="login-failure"
                    role="alert"
                  >
                    {error}
                  </div>
                ) : null}

                <Button
                  className="login-threshold__primary-action"
                  disabled={!canSubmit || loading}
                  size="lg"
                  type="submit"
                >
                  {loading ? "ENTERING…" : "ENTER WORKSPACE"}
                </Button>
              </form>

              {showRegistration ? (
                <p className="login-threshold__registration">
                  New to Codexify? <a href="/register">Create a user profile</a>
                </p>
              ) : null}
            </>
          )}
        </div>
      </section>
    </main>
  );
}
