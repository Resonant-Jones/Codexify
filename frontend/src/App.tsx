import React from "react";
import AppShell from "./components/persona/layout/AppShell";
import { TopBar } from "./components/TopBar";
import EventsConsole from "./pages/EventsConsole";

/**
 * App entry with a gated UI Playground ("Tune Rack").
 *
 * When the env flag VITE_TUNE=1 is set (or in plain DEV),
 * visiting the route /dev/tune will try to load the sandboxed
 * playground from ./dev/ui-tune/UITunePad and its scoped CSS.
 *
 * This never touches production UI unless you intentionally
 * navigate to /dev/tune with the flag enabled.
 */

const TUNE_ENABLED = (import.meta as any)?.env?.DEV || (import.meta as any)?.env?.VITE_TUNE === "1";

function isTuneRoute() {
  if (typeof window === "undefined") return false;
  return window.location.pathname.startsWith("/dev/tune");
}

function isEventsRoute() {
  if (typeof window === "undefined") return false;
  return window.location.pathname.startsWith("/dev/events");
}

function DevTuneGate() {
  const [Mod, setMod] = React.useState<React.ComponentType | null>(null);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    // Load the CSS first (scoped inside UITunePad via .tune-sandbox)
    import("./dev/ui-tune/ui-tune.dev.css").catch(() => {
      // Non-fatal if CSS not present yet
    });

    // Dynamically import the playground component only on the dev route
    import("./dev/ui-tune/UITunePad")
      .then((m) => {
        if (cancelled) return;
        const Comp = (m as any).default || (m as any).UITunePad || (m as any);
        if (typeof Comp === "function") setMod(() => Comp);
        else setError(new Error("UITunePad module did not export a component"));
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e : new Error(String(e)));
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div style={{ padding: 16, fontFamily: "ui-sans-serif, system-ui" }}>
        <strong>UI Tune Rack not found.</strong>
        <div style={{ opacity: 0.75, marginTop: 8 }}>
          Create <code>src/dev/ui-tune/UITunePad.tsx</code> and
          <code> src/dev/ui-tune/ui-tune.dev.css</code>, or disable the tune route.
        </div>
      </div>
    );
  }

  if (!Mod) {
    return null; // simple fade-in once loaded
  }

  const Comp = Mod;
  return <Comp />;
}

export default function App() {
  if (TUNE_ENABLED && isTuneRoute()) {
    return <DevTuneGate />;
  }
  if (isEventsRoute()) {
    return (
      <div style={{ minHeight: "100svh", display: "flex", flexDirection: "column" }}>
        <TopBar />
        <main style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
          <EventsConsole />
        </main>
      </div>
    );
  }
  return <AppShell />;
}
