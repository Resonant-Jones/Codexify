import React from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

import CompletionReplayPage from "./CompletionReplayPage";

function getOperatorSection(pathname: string): "completion-replay" | "unknown" {
  if (pathname === "/operator" || pathname === "/operator/") {
    return "completion-replay";
  }
  if (pathname.startsWith("/operator/replay")) {
    return "completion-replay";
  }
  return "unknown";
}

export function OperatorConsoleShell() {
  const pathname =
    typeof window === "undefined" ? "/operator" : window.location.pathname;
  const section = getOperatorSection(pathname);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.18),_transparent_32%),linear-gradient(180deg,_#05070b_0%,_#0b1220_48%,_#05070b_100%)] text-[var(--text)]">
      <header className="border-b border-white/10 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-start justify-between gap-4 px-4 py-5">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">
                Operator Console
              </h1>
              <Badge className="border border-sky-400/40 bg-sky-400/15 text-sky-100">
                Debug Surface
              </Badge>
            </div>
            <p className="mt-2 max-w-3xl text-sm text-[var(--muted)]">
              Operator-facing observability shell for replaying a real completion
              request and inspecting the inputs, retrieval trace, and output that the
              current API can actually expose.
            </p>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-4 px-4 py-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside>
          <Card className="border-[var(--panel-border)] bg-[var(--panel-bg)]/85 text-[var(--text)]">
            <CardContent className="space-y-3 p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-subtle)]">
                Console
              </div>
              <a
                href="/operator"
                className="block rounded-2xl border border-sky-400/40 bg-sky-400/15 px-4 py-3 text-sm font-medium text-sky-50 transition hover:bg-sky-400/20"
                aria-current={section === "completion-replay" ? "page" : undefined}
              >
                Completion Replay
                <div className="mt-1 text-xs font-normal text-sky-100/80">
                  Inspect one run end to end.
                </div>
              </a>
              <div className="rounded-2xl border border-dashed border-[var(--panel-border)] bg-white/4 px-4 py-3 text-sm text-[var(--muted)]">
                Future operator tabs can live here without sharing the primary chat shell.
              </div>
            </CardContent>
          </Card>
        </aside>

        <main>
          {section === "completion-replay" ? (
            <CompletionReplayPage />
          ) : (
            <Card className="border-[var(--panel-border)] bg-[var(--panel-bg)]/85 text-[var(--text)]">
              <CardContent className="p-6 text-sm text-[var(--muted)]">
                This operator route exists, but the requested section is not implemented
                yet.
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </div>
  );
}

export default OperatorConsoleShell;
