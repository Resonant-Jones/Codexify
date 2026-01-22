import React from "react";

import DocumentGenModal, {
  DocumentGenInput,
} from "./components/DocumentGenModal";
import { Button } from "./components/ui/button";
import AppShell from "./components/persona/layout/AppShell";
import { TopBar } from "./components/TopBar";
import EventsConsole from "./pages/EventsConsole";
import { SharePage } from "./pages/SharePage";

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

function isShareRoute() {
  if (typeof window === "undefined") return false;
  return window.location.pathname.startsWith("/share/");
}

function getShareToken() {
  if (typeof window === "undefined") return null;
  const match = window.location.pathname.match(/^\/share\/(.+)$/);
  return match ? match[1] : null;
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
  const [docGenOpen, setDocGenOpen] = React.useState(false);
  const [docGenDraft, setDocGenDraft] = React.useState<DocumentGenInput | null>(
    null
  );

  const handleDocGenSubmit = React.useCallback(
    (input: DocumentGenInput) => {
      setDocGenDraft(input);
      try {
        window.dispatchEvent(
          new CustomEvent("cfy:toast", {
            detail: { message: "Document draft captured" },
          })
        );
      } catch {
        // ignore
      }
    },
    []
  );

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
  if (isShareRoute()) {
    const token = getShareToken();
    if (token) {
      return <SharePage token={token} />;
    }
  }
  return (
    <>
      <AppShell />
      <div className="fixed bottom-6 right-6 z-[1200]">
        <Button
          type="button"
          variant="ghost"
          className="rounded-full px-4 shadow"
          onClick={() => setDocGenOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={docGenOpen}
        >
          Generate Doc
        </Button>
      </div>
      <DocumentGenModal
        open={docGenOpen}
        onOpenChange={setDocGenOpen}
        onSubmit={handleDocGenSubmit}
        initialValues={docGenDraft ?? undefined}
      />
    </>
  );
}
