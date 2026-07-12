import { useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth/useAuth";
import { getRuntimeConfigSync } from "@/lib/runtimeConfig";

const LOGIN_FAILURE_MESSAGE =
  "Unable to sign in. Check your credentials and try again.";

export default function LoginPage() {
  const auth = useAuth();
  const remoteAuthMode = getRuntimeConfigSync().authMode === "remote";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(
    () => username.trim().length > 0 && password.trim().length > 0,
    [password, username]
  );

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

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md rounded-[var(--radius-tile,19px)] border border-[var(--panel-border)] bg-[var(--panel-bg)]/95 p-8 text-[var(--text)] shadow-2xl backdrop-blur-xl">
        {/* ── Brand + context label ── */}
        <div className="mb-6 space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-subtle)]">
            Codexify
          </p>
          <div className="flex items-baseline gap-3">
            <h1 className="text-3xl font-semibold tracking-[-0.03em]">
              {remoteAuthMode ? "Session sign-in" : "Sign in"}
            </h1>
            <span className="rounded-full bg-[var(--accent)]/15 px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wider text-[var(--accent)]">
              Returning user
            </span>
          </div>
          <p className="text-sm leading-6 text-[var(--text-subtle)]">
            {remoteAuthMode
              ? "Use your workspace username and password. This browser will receive a session token after sign-in."
              : "Use your username and password to open the workspace."}
          </p>
        </div>

        {/* ── Sign-in form ── */}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-[var(--text)]">Username</span>
            <input
              className="w-full rounded-[var(--radius-tile,19px)] border border-[var(--panel-border)] bg-[var(--chip-bg)] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-subtle)]/50 outline-none transition focus:border-[var(--accent)]/60 focus:bg-[var(--chip-bg)] focus:ring-1 focus:ring-[var(--accent)]/30"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Enter your username"
              autoComplete="username"
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-[var(--text)]">Password</span>
            <input
              className="w-full rounded-[var(--radius-tile,19px)] border border-[var(--panel-border)] bg-[var(--chip-bg)] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-subtle)]/50 outline-none transition focus:border-[var(--accent)]/60 focus:bg-[var(--chip-bg)] focus:ring-1 focus:ring-[var(--accent)]/30"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
            />
          </label>

          {error ? (
            <div
              className="rounded-[var(--radius-tile,19px)] border border-[var(--danger-border)] bg-[var(--danger-surface)] px-4 py-3 text-sm text-[var(--danger-text)]"
              role="alert"
            >
              {error}
            </div>
          ) : null}

          <Button
            type="submit"
            className="w-full"
            disabled={!canSubmit || loading}
          >
            {loading ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        {import.meta.env.VITE_PRIVATE_PREVIEW !== "true" && (
          <>
            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-[var(--panel-border)]" />
              <span className="text-xs text-[var(--text-subtle)]">or</span>
              <div className="h-px flex-1 bg-[var(--panel-border)]" />
            </div>
            <div className="rounded-[var(--radius-tile,19px)] border border-[var(--panel-border)] bg-[var(--surface-soft)] p-4 text-center">
              <p className="text-sm text-[var(--text-subtle)]">New to Codexify?</p>
              <a className="mt-1.5 inline-block text-sm font-semibold text-[var(--accent)] underline underline-offset-4 hover:text-[var(--accent-strong)] transition-colors" href="/register">
                Create a user profile →
              </a>
            </div>
          </>
        )}

        {auth.ready && auth.isAuthenticated ? (
          <div className="mt-4 text-xs text-emerald-300">
            A session is already active.
          </div>
        ) : null}
      </div>
    </main>
  );
}
