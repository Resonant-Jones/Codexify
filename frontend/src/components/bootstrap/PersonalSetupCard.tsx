import React from "react";
import { Button } from "@/components/ui/button";
import type { BootstrapReadiness } from "@/contracts/bootstrapReadiness.generated";
import { BootstrapHumanAction } from "@/contracts/bootstrapReadiness.generated";
import { isTauriRuntime } from "@/lib/runtimeConfig";
import { runSetupCli } from "@/lib/runtimeBootstrap";

const DISMISSED_KEY = "cfy.bootstrap.personalSetupDismissed.v1";

export default function PersonalSetupCard({ readiness, onOpenSettings }: {
  readiness: BootstrapReadiness;
  onOpenSettings: () => void;
}) {
  const [dismissed, setDismissed] = React.useState(() => {
    try { return localStorage.getItem(DISMISSED_KEY) === "true"; } catch { return false; }
  });
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [action, setAction] = React.useState<BootstrapReadiness["humanAction"] | null>(null);
  const setVisibility = (hide: boolean) => {
    setDismissed(hide);
    try { localStorage.setItem(DISMISSED_KEY, String(hide)); } catch { /* Storage may be unavailable. */ }
  };

  const finish = async () => {
    setBusy(true);
    try {
      // The existing native helper owns local configuration. A web client has no host authority.
      if (isTauriRuntime()) {
        const result = await runSetupCli();
        if (!result.ok) {
          setAction(BootstrapHumanAction.PREREQUISITE_UNAVAILABLE);
          setMessage("Local defaults could not be applied. Resume setup in the desktop launcher; your configuration is preserved.");
          return;
        }
      }
      setAction(BootstrapHumanAction.PROVIDER_MODEL_CHOICE_REQUIRED);
      setMessage("Safe local defaults are in place. Choose your provider and model before continuing. Credentials, installations, downloads, external accounts, and permissions require your decision.");
    } catch {
      setAction(BootstrapHumanAction.PREREQUISITE_UNAVAILABLE);
      setMessage("Setup could not continue. Resume the desktop launcher or run ./scripts/setup from your checkout.");
    } finally { setBusy(false); }
  };

  if (!readiness.coreReady || readiness.inferenceReady) return null;
  if (dismissed) return (
    <div className="flex justify-end py-2">
      <Button variant="ghost" onClick={() => setVisibility(false)}>Resume personal setup · Chat unavailable</Button>
    </div>
  );
  return (
    <section aria-label="Personal setup" data-human-action={action ?? readiness.humanAction}
      className="my-3 rounded-xl border p-4" style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)", color: "var(--text)" }}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold">Finish personal setup</h2>
        <Button variant="ghost" disabled={busy} onClick={() => setVisibility(true)}>Later</Button>
      </div>
      <p className="my-2 text-sm">Your workspace is available. Chat is unavailable until your chosen local provider and model pass their health checks.</p>
      <p role="status" className="my-2 text-sm">{message ?? "No inference runtime or model will be installed automatically. You can keep using available workspace surfaces."}</p>
      <div className="flex flex-wrap gap-2">
        <Button disabled={busy} onClick={() => void finish()}>{busy ? "Applying local defaults…" : "Finish personal setup"}</Button>
        <Button variant="outline" onClick={onOpenSettings}>Open Settings</Button>
      </div>
    </section>
  );
}
