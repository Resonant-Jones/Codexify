import { useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import api from "@/lib/api";

export default function RegisterPage() {
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
      await api.post("/auth/register", {
        username: username.trim(),
        password,
      });
      window.location.assign("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
              Create account
            </h1>
            <span className="rounded-full bg-[var(--tag-surface)] px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wider text-[var(--tag-text)]">
              New user
            </span>
          </div>
          <p className="text-sm leading-6 text-[var(--text-subtle)]">
            Register a new local user for this workspace.
          </p>
        </div>

        {/* ── Registration form ── */}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-[var(--text)]">
              Choose a username
            </span>
            <input
              className="w-full rounded-[var(--radius-tile,19px)] border border-[var(--panel-border)] bg-[var(--chip-bg)] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-subtle)]/50 outline-none transition focus:border-[var(--accent)]/60 focus:bg-[var(--chip-bg)] focus:ring-1 focus:ring-[var(--accent)]/30"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="e.g. resonant-jones"
              autoComplete="username"
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-[var(--text)]">
              Choose a password
            </span>
            <input
              className="w-full rounded-[var(--radius-tile,19px)] border border-[var(--panel-border)] bg-[var(--chip-bg)] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-subtle)]/50 outline-none transition focus:border-[var(--accent)]/60 focus:bg-[var(--chip-bg)] focus:ring-1 focus:ring-[var(--accent)]/30"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Create a strong password"
              autoComplete="new-password"
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
            {loading ? "Creating..." : "Create account"}
          </Button>
        </form>

        {/* ── Divider ── */}
        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-[var(--panel-border)]" />
          <span className="text-xs text-[var(--text-subtle)]">or</span>
          <div className="h-px flex-1 bg-[var(--panel-border)]" />
        </div>

        {/* ── Sign-in callout ── */}
        <div className="rounded-[var(--radius-tile,19px)] border border-[var(--panel-border)] bg-[var(--surface-soft)] p-4 text-center">
          <p className="text-sm text-[var(--text-subtle)]">
            Already have a profile?
          </p>
          <a
            className="mt-1.5 inline-block text-sm font-semibold text-[var(--accent)] underline underline-offset-4 hover:text-[var(--accent-strong)] transition-colors"
            href="/login"
          >
            Sign in to your workspace →
          </a>
        </div>
      </div>
    </main>
  );
}
