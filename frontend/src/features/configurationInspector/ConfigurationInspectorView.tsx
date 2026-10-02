import { useEffect, useRef, useState, type ReactNode } from "react";
import { isAxiosError } from "axios";
import { Button } from "@/components/ui/button";
import { getConfigurationSnapshot } from "./api";
import type { ConfigurationEvidence, ConfigurationSnapshot } from "./contracts";

const EVIDENCE_MEANINGS: Record<ConfigurationEvidence, string> = {
  declared: "A source declares this value; owner selection is not established.",
  resolved: "The named owner reports a selected value for this scope.",
  observed: "Runtime evidence establishes this state for the responding process.",
  unavailable: "This value cannot safely be determined or exposed.",
};

const UNAVAILABLE_REASONS = {
  supported_profile_state_unavailable: "Supported profile state unavailable.",
  mounted_route_inventory_unavailable: "Mounted route inventory unavailable.",
  provider_egress_posture_unavailable: "Provider / egress posture unavailable.",
  local_inference_target_unavailable: "Local inference target unavailable.",
};

type LoadState =
  | { kind: "loading" }
  | { kind: "loaded"; snapshot: ConfigurationSnapshot }
  | { kind: "denied" | "unavailable" | "error" };

function EvidenceLabel({ evidence }: { evidence: ConfigurationEvidence }) {
  return (
    <span className="inline-flex rounded-[var(--radius-micro)] border border-[var(--panel-border)] px-2 py-1 text-xs"
      title={EVIDENCE_MEANINGS[evidence]} data-evidence={evidence}>
      {evidence.charAt(0).toUpperCase() + evidence.slice(1)}
    </span>
  );
}

function EvidenceCard({ title, section, children, note }: {
  title: string;
  section: { evidence: ConfigurationEvidence; owner: string; unavailable_reason: keyof typeof UNAVAILABLE_REASONS | null };
  children: ReactNode;
  note?: string;
}) {
  return (
    <section aria-label={title} className="min-w-0 space-y-3 rounded-[var(--tile-radius)] border border-[var(--panel-border)] p-[var(--card-pad)]"
      style={{ background: "var(--panel-bg)" }}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold">{title}</h2>
        <EvidenceLabel evidence={section.evidence} />
      </div>
      <p className="text-xs" style={{ color: "var(--muted)" }}>{EVIDENCE_MEANINGS[section.evidence]}</p>
      <p className="text-xs" style={{ color: "var(--muted)", overflowWrap: "anywhere" }}>
        Owner: <code>{section.owner}</code>
      </p>
      {section.evidence === "unavailable" ? (
        <p className="text-sm">{section.unavailable_reason && UNAVAILABLE_REASONS[section.unavailable_reason]}</p>
      ) : children}
      {note && <p className="text-xs" style={{ color: "var(--muted)" }}>{note}</p>}
    </section>
  );
}

function ValueRow({ label, value }: { label: string; value: string | number | boolean | null }) {
  if (value === null) return null;
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:justify-between sm:gap-4">
      <dt className="text-sm" style={{ color: "var(--muted)" }}>{label}</dt>
      <dd className="min-w-0 text-sm sm:text-right" style={{ overflowWrap: "anywhere" }}>
        {typeof value === "boolean" ? (value ? "Yes" : "No") : value}
      </dd>
    </div>
  );
}

export default function ConfigurationInspectorView({ onBackToSettings, snapshotRequest }: {
  onBackToSettings: () => void;
  /** AppShell retains only this opening's request across compositor remounts. */
  snapshotRequest?: { current: Promise<ConfigurationSnapshot> | null };
}) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [revision, setRevision] = useState(0);
  const localRequest = useRef<Promise<ConfigurationSnapshot> | null>(null);
  const request = snapshotRequest ?? localRequest;

  useEffect(() => {
    let active = true;
    // Reuse this opening's request during StrictMode and compositor remounts.
    request.current ??= getConfigurationSnapshot();
    request.current.then(
      (snapshot) => { if (active) setState({ kind: "loaded", snapshot }); },
      (error: unknown) => {
        if (!active) return;
        const status = isAxiosError(error) ? error.response?.status : undefined;
        setState({ kind: status === 401 || status === 403 ? "denied" : status === 404 ? "unavailable" : "error" });
      }
    );
    return () => { active = false; };
  }, [revision, request]);

  const snapshot = state.kind === "loaded" ? state.snapshot : null;
  return (
    <div className="min-w-0 space-y-[var(--shell-gap)] p-[var(--card-pad)]" style={{ color: "var(--text)" }}>
      <header className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Button variant="ghost" onClick={onBackToSettings}>Back to Settings</Button>
          <Button variant="ghost" disabled={state.kind === "loading"} onClick={() => {
            setState({ kind: "loading" });
            request.current = getConfigurationSnapshot();
            setRevision((current) => current + 1);
          }}>Refresh</Button>
        </div>
        <h1 className="text-xl font-semibold">Configuration Inspector</h1>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Read-only installation/operator posture, reflecting the responding Guardian process.
        </p>
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          Configuration evidence is separate from runtime health and release support.
        </p>
        {snapshot && (
          <dl className="space-y-2">
            <ValueRow label="Generated" value={snapshot.generated_at} />
            <ValueRow label="Process ID" value={snapshot.process.process_id} />
            <ValueRow label="Scope" value={snapshot.process.scope} />
          </dl>
        )}
      </header>
      <div aria-live="polite" aria-busy={state.kind === "loading"}>
        {state.kind === "loading" && <p className="text-sm">Loading configuration snapshot…</p>}
        {state.kind === "denied" && <div><h2 className="font-semibold">Operator access required</h2><p className="text-sm">This view requires Guardian operator authority.</p></div>}
        {state.kind === "unavailable" && <h2 className="font-semibold">Configuration Inspector unavailable in this runtime profile</h2>}
        {state.kind === "error" && <div><h2 className="font-semibold">Unable to load configuration snapshot</h2><p className="text-sm">Select Refresh to retry.</p></div>}
      </div>
      {snapshot && (
        <div className="grid min-w-0 grid-cols-1 gap-[var(--shell-gap)] lg:grid-cols-2">
          <EvidenceCard title="Supported Profile" section={snapshot.supported_profile}>
            <dl className="space-y-2">
              <ValueRow label="Profile name" value={snapshot.supported_profile.profile_name} />
              <ValueRow label="Version" value={snapshot.supported_profile.version} />
              <ValueRow label="Surface class" value={snapshot.supported_profile.surface_class} />
              <ValueRow label="Valid profile posture" value={snapshot.supported_profile.valid} />
            </dl>
          </EvidenceCard>
          <EvidenceCard title="Mounted Routes" section={snapshot.mounted_routes} note="Mounted only — not authorization, health, or release support.">
            <ul aria-label="Mounted route families" className="flex flex-wrap gap-2">
              {snapshot.mounted_routes.route_families?.map((family) => (
                <li key={family} className="max-w-full rounded-[var(--radius-micro)] border border-[var(--panel-border)] px-2 py-1 text-xs" style={{ overflowWrap: "anywhere" }}>{family}</li>
              ))}
            </ul>
          </EvidenceCard>
          <EvidenceCard title="Provider & Egress" section={snapshot.provider_egress}>
            <dl className="space-y-2">
              <ValueRow label="Configured provider class" value={snapshot.provider_egress.configured_provider_class} />
              <ValueRow label="Local-only mode" value={snapshot.provider_egress.local_only_mode} />
              <ValueRow label="Cloud providers allowed" value={snapshot.provider_egress.cloud_providers_allowed} />
              <ValueRow label="Egress allowlist configured" value={snapshot.provider_egress.egress_allowlist_configured} />
            </dl>
          </EvidenceCard>
          <EvidenceCard title="Local Inference" section={snapshot.local_inference}>
            <dl className="space-y-2">
              <ValueRow label="Provider class" value={snapshot.local_inference.provider_class} />
              <ValueRow label="Configured target" value={snapshot.local_inference.configured_target} />
            </dl>
          </EvidenceCard>
        </div>
      )}
    </div>
  );
}
