import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import api from "@/lib/api";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
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
      <div className="w-full max-w-md rounded-[28px] border border-white/10 bg-slate-950/90 p-8 text-slate-100 shadow-2xl">
        <div className="mb-6 space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            Codexify
          </p>
          <h1 className="text-3xl font-semibold tracking-[-0.03em]">
            Create account
          </h1>
          <p className="text-sm leading-6 text-slate-400">
            Register a new local user for this workspace.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block space-y-2">
            <span className="text-sm text-slate-300">Username</span>
            <input
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-white/30"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm text-slate-300">Password</span>
            <input
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-white/30"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
            />
          </label>

          {error ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          ) : null}

          <Button type="submit" className="w-full rounded-2xl" disabled={loading}>
            {loading ? "Creating..." : "Create account"}
          </Button>
        </form>

        <div className="mt-6 text-sm text-slate-400">
          Already registered?{" "}
          <a className="text-slate-100 underline" href="/login">
            Sign in
          </a>
        </div>
      </div>
    </main>
  );
}
