import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  GuardianDelegationTranscriptItem,
  GuardianDelegationTranscriptMetadata,
  GuardianDelegationTranscriptMetadataKey,
  GuardianDelegationTranscriptResponse,
  GuardianDelegationTranscriptScalar,
} from "@/contracts/guardianDelegationTranscript";
import {
  getGuardianDelegationTranscript,
  GuardianDelegationTranscriptError,
} from "@/lib/guardianDelegations";

type ViewerStatus =
  | "empty"
  | "error"
  | "loaded"
  | "loading"
  | "not_found"
  | "unavailable";

export interface GuardianDelegationTranscriptViewerProps {
  intentId: string;
}

const SAFE_METADATA_KEYS: GuardianDelegationTranscriptMetadataKey[] = [
  "intent_id",
  "run_id",
  "thread_id",
  "source_message_id",
  "delivery_key",
  "result_message_id",
  "approval_state",
  "approval_source",
  "approval_mode",
  "intent_status",
  "run_status",
  "visibility_status",
];

const SECRET_LIKE_PATTERN =
  /(sk-[a-z0-9_-]{8,}|gh[pousr]_[a-z0-9_]{8,}|api[_-]?key|access[_-]?token|secret|-----BEGIN)/i;

function isScalar(value: unknown): value is GuardianDelegationTranscriptScalar {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  );
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function formatLabel(value: string): string {
  const normalized = value.trim().replace(/[_-]+/g, " ");
  if (!normalized) return "Unknown";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function boundedText(value: unknown, maxLength = 180): string {
  if (!isScalar(value)) return "Not available";
  const normalized = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!normalized) return "Not available";
  if (SECRET_LIKE_PATTERN.test(normalized)) return "[redacted]";
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
}

function stateText(value: unknown): string {
  const text = boundedText(value, 96);
  return text === "Not available" || text === "[redacted]"
    ? text
    : formatLabel(text);
}

function panelStyle(): React.CSSProperties {
  return {
    background: "var(--surface-soft)",
    border: "1px solid var(--panel-border)",
    borderRadius: "var(--tile-radius)",
    padding: "var(--card-pad)",
  };
}

function StatusPanel({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "danger" | "neutral";
}) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className="text-sm leading-6"
      style={{
        ...panelStyle(),
        color: tone === "danger" ? "var(--danger-text)" : "var(--muted)",
      }}
    >
      {children}
    </div>
  );
}

function DetailRow({
  label,
  value,
  testId,
}: {
  label: string;
  value: unknown;
  testId?: string;
}) {
  return (
    <div
      className="grid gap-2 text-sm sm:grid-cols-[12rem_minmax(0,1fr)]"
      data-testid={testId}
    >
      <dt className="font-medium" style={{ color: "var(--muted)" }}>
        {label}
      </dt>
      <dd className="min-w-0 break-words" style={{ color: "var(--text)" }}>
        {boundedText(value)}
      </dd>
    </div>
  );
}

function StateChip({ label, value }: { label: string; value: unknown }) {
  return (
    <div
      className="flex min-w-0 items-center justify-between gap-3 border text-sm"
      style={{
        background: "var(--panel-bg)",
        borderColor: "var(--panel-border)",
        borderRadius: "var(--tile-radius)",
        color: "var(--text)",
        padding: "var(--card-pad)",
      }}
    >
      <span className="min-w-0 font-medium" style={{ color: "var(--muted)" }}>
        {label}
      </span>
      <Badge
        className="max-w-full border text-[11px]"
        style={{
          background: "var(--surface-soft)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
        }}
      >
        <span className="min-w-0 break-words">{stateText(value)}</span>
      </Badge>
    </div>
  );
}

function safeMetadataEntries(
  metadata: GuardianDelegationTranscriptMetadata | null | undefined
): Array<[GuardianDelegationTranscriptMetadataKey, GuardianDelegationTranscriptScalar]> {
  if (!metadata || typeof metadata !== "object") return [];
  return SAFE_METADATA_KEYS.flatMap((key) => {
    const value = metadata[key];
    if (!hasValue(value) || !isScalar(value)) return [];
    return [[key, value] as [
      GuardianDelegationTranscriptMetadataKey,
      GuardianDelegationTranscriptScalar,
    ]];
  });
}

function TranscriptItemRow({
  index,
  item,
}: {
  index: number;
  item: GuardianDelegationTranscriptItem;
}) {
  const metadataEntries = safeMetadataEntries(item.metadata);
  return (
    <li
      className="space-y-3 border"
      data-testid={`guardian-delegation-transcript-item-${index}`}
      style={panelStyle()}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge
          className="border text-[11px]"
          style={{
            background: "var(--surface-soft)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
          }}
        >
          {formatLabel(item.kind)}
        </Badge>
        <span className="text-xs" style={{ color: "var(--muted)" }}>
          {formatLabel(item.source)}
        </span>
        {hasValue(item.created_at) ? (
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            {boundedText(item.created_at, 72)}
          </span>
        ) : null}
      </div>
      <p className="break-words text-sm leading-6" style={{ color: "var(--text)" }}>
        {boundedText(item.summary, 360)}
      </p>
      {metadataEntries.length > 0 ? (
        <dl className="grid gap-2 sm:grid-cols-2">
          {metadataEntries.map(([key, value]) => (
            <div key={key} className="min-w-0 text-xs leading-5">
              <dt className="font-medium" style={{ color: "var(--muted)" }}>
                {formatLabel(key)}
              </dt>
              <dd className="break-words" style={{ color: "var(--text)" }}>
                {boundedText(value, 140)}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
    </li>
  );
}

function LoadedTranscript({
  transcript,
}: {
  transcript: GuardianDelegationTranscriptResponse;
}) {
  const sourceThread = transcript.source_thread_reference ?? {};
  const threadId = sourceThread.thread_id ?? transcript.thread_id;
  const sourceMessageId =
    sourceThread.source_message_id ?? transcript.source_message_id;
  const items = Array.isArray(transcript.transcript_items)
    ? transcript.transcript_items
    : [];

  return (
    <div className="space-y-4">
      <section className="space-y-3" style={panelStyle()}>
        <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          Intent lineage
        </h3>
        <dl className="space-y-2">
          <DetailRow label="Intent id" value={transcript.intent_id} />
          <DetailRow label="Thread id" value={threadId} />
          <DetailRow label="Source message id" value={sourceMessageId} />
          {hasValue(transcript.project_id) ? (
            <DetailRow label="Project id" value={transcript.project_id} />
          ) : null}
          {hasValue(transcript.run_id) ? (
            <DetailRow label="Run id" value={transcript.run_id} />
          ) : null}
        </dl>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          Delegation state
        </h3>
        <div className="grid gap-3 md:grid-cols-2">
          <StateChip label="Approval mode" value={transcript.approval_mode} />
          <StateChip label="Approval state" value={transcript.approval_state} />
          <StateChip label="Approval source" value={transcript.approval_source} />
          <StateChip label="Intent status" value={transcript.intent_status} />
          <StateChip label="Run status" value={transcript.run_status} />
          <StateChip
            label="Visibility status"
            value={transcript.visibility_status}
          />
        </div>
      </section>

      {hasValue(transcript.result_message_id) ||
      hasValue(transcript.result_delivered_at) ? (
        <section className="space-y-3" style={panelStyle()}>
          <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            Result metadata
          </h3>
          <dl className="space-y-2">
            {hasValue(transcript.result_message_id) ? (
              <DetailRow
                label="Result message id"
                value={transcript.result_message_id}
              />
            ) : null}
            {hasValue(transcript.result_delivered_at) ? (
              <DetailRow
                label="Delivered at"
                value={transcript.result_delivered_at}
              />
            ) : null}
          </dl>
        </section>
      ) : null}

      <section className="space-y-3">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          Transcript items
        </h3>
        {items.length === 0 ? (
          <StatusPanel>No transcript items are available for this inspection.</StatusPanel>
        ) : (
          <ol className="space-y-3">
            {items.map((item, index) => (
              <TranscriptItemRow
                key={item.item_id || `${item.kind}:${index}`}
                index={index}
                item={item}
              />
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

function resolveFailureState(error: unknown): {
  message: string;
  status: ViewerStatus;
} {
  if (GuardianDelegationTranscriptError.isInstance(error)) {
    if (error.kind === "not_found") {
      return {
        message: "No Guardian delegation intent exists for that id.",
        status: "not_found",
      };
    }
    return {
      message:
        "Guardian delegation transcript inspection is internal-only or unavailable in this runtime posture.",
      status: "unavailable",
    };
  }

  return {
    message:
      error instanceof Error && error.message
        ? boundedText(error.message, 180)
        : "Unable to load Guardian delegation transcript inspection.",
    status: "error",
  };
}

export default function GuardianDelegationTranscriptViewer({
  intentId,
}: GuardianDelegationTranscriptViewerProps) {
  const normalizedIntentId = intentId.trim();
  const [status, setStatus] = React.useState<ViewerStatus>(
    normalizedIntentId ? "loading" : "empty"
  );
  const [failureMessage, setFailureMessage] = React.useState<string | null>(null);
  const [transcript, setTranscript] =
    React.useState<GuardianDelegationTranscriptResponse | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    if (!normalizedIntentId) {
      setStatus("empty");
      setTranscript(null);
      setFailureMessage(null);
      return () => {
        cancelled = true;
      };
    }

    setStatus("loading");
    setTranscript(null);
    setFailureMessage(null);
    void getGuardianDelegationTranscript(normalizedIntentId)
      .then((response) => {
        if (cancelled) return;
        setTranscript(response);
        setStatus("loaded");
      })
      .catch((error) => {
        if (cancelled) return;
        const failure = resolveFailureState(error);
        setFailureMessage(failure.message);
        setStatus(failure.status);
      });

    return () => {
      cancelled = true;
    };
  }, [normalizedIntentId]);

  return (
    <Card
      className="bezel-none border"
      data-testid="guardian-delegation-transcript-viewer"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
      <CardHeader
        className="space-y-2"
        style={{
          borderBottom: "1px solid var(--panel-border)",
          padding: "var(--card-pad)",
        }}
      >
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            className="border text-[11px]"
            style={{
              background: "var(--surface-soft)",
              borderColor: "var(--panel-border)",
              color: "var(--muted)",
            }}
          >
            Inspection only
          </Badge>
          {transcript?.inspection_only === false ? (
            <Badge
              className="border text-[11px]"
              style={{
                background: "var(--danger-surface)",
                borderColor: "var(--danger-border)",
                color: "var(--danger-text)",
              }}
            >
              Projection flag not confirmed
            </Badge>
          ) : null}
        </div>
        <CardTitle className="text-base" style={{ color: "var(--text)" }}>
          Guardian delegation transcript
        </CardTitle>
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Read-only projection from the Guardian delegation transcript endpoint.
        </p>
      </CardHeader>

      <CardContent className="space-y-4" style={{ padding: "var(--card-pad)" }}>
        {status === "empty" ? (
          <StatusPanel>Enter a Guardian delegation intent id to inspect its transcript projection.</StatusPanel>
        ) : null}
        {status === "loading" ? (
          <StatusPanel>Loading Guardian delegation transcript projection...</StatusPanel>
        ) : null}
        {status === "not_found" ? (
          <StatusPanel>{failureMessage}</StatusPanel>
        ) : null}
        {status === "unavailable" ? (
          <StatusPanel>{failureMessage}</StatusPanel>
        ) : null}
        {status === "error" ? (
          <StatusPanel tone="danger">{failureMessage}</StatusPanel>
        ) : null}
        {status === "loaded" && transcript ? (
          <LoadedTranscript transcript={transcript} />
        ) : null}
      </CardContent>
    </Card>
  );
}
