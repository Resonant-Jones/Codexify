import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { useAuth } from "@/components/auth/useAuth";
import { Button } from "@/components/ui/button";
import { getRuntimeConfigSync } from "@/lib/runtimeConfig";
import api from "@/lib/api";

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
  const scoutParams = new URLSearchParams(window.location.search);
  const scoutState = scoutParams.get("scout_state") ?? "";
  const scoutChallenge = scoutParams.get("scout_challenge") ?? "";
  const scoutFlow = /^[A-Za-z0-9_-]{43}$/.test(scoutState) &&
    /^[A-Za-z0-9_-]{43}$/.test(scoutChallenge) &&
    scoutParams.getAll("scout_state").length === 1 &&
    scoutParams.getAll("scout_challenge").length === 1;
  const [handoffLoading, setHandoffLoading] = useState(false);
  const showRegistration = import.meta.env.VITE_PRIVATE_PREVIEW !== "true";
  const identityLabel = remoteAuthMode ? "Email address" : "Username";

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
      setPassword("");
      if (!scoutFlow) window.location.assign("/");
    } catch {
      setError(LOGIN_FAILURE_MESSAGE);
    } finally {
      setLoading(false);
    }
  }

  async function continueToScout() {
    if (!scoutFlow || !activeSession || handoffLoading) return;
    setHandoffLoading(true);
    setError(null);
    try {
      const response = await api.post("/auth/scout/handoff", {
        state: scoutState, challenge: scoutChallenge,
      });
      const callback = new URL(String(response.data?.callback ?? ""));
      if (callback.protocol !== "ai.resonantconstructs.codexify.scout:" ||
          callback.hostname !== "access-callback" || callback.pathname !== "" ||
          callback.username || callback.password || callback.port || callback.hash ||
          callback.searchParams.getAll("state").length !== 1 ||
          callback.searchParams.get("state") !== scoutState ||
          callback.searchParams.getAll("code").length !== 1 ||
          !/^[A-Za-z0-9_-]{43}$/.test(callback.searchParams.get("code") ?? "")) {
        throw new Error("Invalid handoff");
      }
      window.location.assign(callback.href);
    } catch {
      setError("Could not continue to Scout. Retry from Scout; your account session remains unchanged.");
    } finally {
      setHandoffLoading(false);
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
        ? "Sign in with the approved email address for this Codexify workspace. This browser will receive a private session token for the active session."
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
              {error ? <p role="alert">{error}</p> : null}
              <Button
                className="login-threshold__primary-action"
                onClick={scoutFlow ? continueToScout : () => window.location.assign("/")}
                disabled={handoffLoading}
                size="lg"
                type="button"
              >
                {scoutFlow ? (handoffLoading ? "Continuing…" : "CONTINUE TO SCOUT") : "CONTINUE TO WORKSPACE"}
              </Button>

              {scoutFlow ? (
                <p>This creates a separate Scout session for your existing account. It has its own expiry and logout, and Scout stores it in this device’s Keychain. Your browser session stays separate.</p>
              ) : null}

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
                  <label htmlFor="login-username">{identityLabel}</label>
                  <input
                    autoComplete={remoteAuthMode ? "email" : "username"}
                    id="login-username"
                    inputMode={remoteAuthMode ? "email" : undefined}
                    onChange={(event) => setUsername(event.target.value)}
                    placeholder={
                      remoteAuthMode
                        ? "you@example.com"
                        : "Enter your username"
                    }
                    ref={usernameInputRef}
                    required
                    type={remoteAuthMode ? "email" : "text"}
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
