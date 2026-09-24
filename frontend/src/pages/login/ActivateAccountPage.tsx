import { useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import api from "@/lib/api";

import "./LoginPage.css";

const ACTIVATION_UNAVAILABLE_MESSAGE =
  "This activation link is unavailable or has expired.";

function captureActivationToken(): string | null {
  if (typeof window === "undefined") return null;

  const fragment = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const token = new URLSearchParams(fragment).get("token")?.trim() || null;
  const cleanUrl = `${window.location.pathname}${window.location.search}`;
  window.history.replaceState(window.history.state, "", cleanUrl);
  return token;
}

export default function ActivateAccountPage() {
  const [token] = useState<string | null>(captureActivationToken);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [loading, setLoading] = useState(false);
  const [succeeded, setSucceeded] = useState(false);
  const [unavailable, setUnavailable] = useState(token === null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const canSubmit = useMemo(
    () =>
      token !== null &&
      password.length > 0 &&
      confirmation.length > 0 &&
      password === confirmation,
    [confirmation, password, token]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading || unavailable || token === null) return;
    if (!password || password !== confirmation) {
      setValidationError("Passwords must be non-empty and match.");
      return;
    }

    setLoading(true);
    setValidationError(null);
    try {
      await api.post("/auth/activate", { token, password });
      setSucceeded(true);
      setPassword("");
      setConfirmation("");
    } catch {
      setUnavailable(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-threshold">
      <div className="login-threshold__atmosphere" aria-hidden="true" />

      <section
        className="login-threshold__composition"
        aria-labelledby="activation-heading"
      >
        <p className="login-threshold__brand">CODEXIFY</p>

        <div className="login-threshold__card">
          <header className="login-threshold__header">
            <p className="login-threshold__eyebrow">PRIVATE WORKSPACE</p>
            <h1 className="login-threshold__heading" id="activation-heading">
              {succeeded ? "Your account is ready" : "Create your account"}
            </h1>
            <p className="login-threshold__body">
              {succeeded
                ? "Your password is set. Sign in through the normal Codexify login."
                : "Choose the password you will use for this Codexify workspace."}
            </p>
          </header>

          {succeeded ? (
            <div className="login-threshold__actions">
              <a
                className="login-threshold__primary-action inline-flex items-center justify-center"
                href="/login"
              >
                CONTINUE TO LOGIN
              </a>
            </div>
          ) : unavailable ? (
            <div className="login-threshold__error" role="alert">
              {ACTIVATION_UNAVAILABLE_MESSAGE}
            </div>
          ) : (
            <form className="login-threshold__form" onSubmit={handleSubmit}>
              <div className="login-threshold__field">
                <label htmlFor="activation-password">New password</label>
                <input
                  autoComplete="new-password"
                  id="activation-password"
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  type="password"
                  value={password}
                />
              </div>

              <div className="login-threshold__field">
                <label htmlFor="activation-password-confirmation">
                  Confirm password
                </label>
                <input
                  aria-describedby={
                    validationError ? "activation-validation-error" : undefined
                  }
                  aria-invalid={validationError ? "true" : undefined}
                  autoComplete="new-password"
                  id="activation-password-confirmation"
                  onChange={(event) => setConfirmation(event.target.value)}
                  required
                  type="password"
                  value={confirmation}
                />
              </div>

              {validationError ? (
                <div
                  className="login-threshold__error"
                  id="activation-validation-error"
                  role="alert"
                >
                  {validationError}
                </div>
              ) : null}

              <Button
                className="login-threshold__primary-action"
                disabled={!canSubmit || loading}
                size="lg"
                type="submit"
              >
                {loading ? "CREATING ACCOUNT…" : "CREATE ACCOUNT"}
              </Button>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}

export { ACTIVATION_UNAVAILABLE_MESSAGE, captureActivationToken };
