import {
  ArrowUpRight,
  Bug,
  MessageSquareText,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

import {
  readGuardianFeedbackOptIn,
  writeGuardianFeedbackOptIn,
} from "../feedbackPreference";

type FeedbackSettingsPanelProps = {
  onStartConversation?: () => void;
};

function FeatureNote({
  children,
  icon: Icon,
  title,
}: {
  children: string;
  icon: LucideIcon;
  title: string;
}) {
  return (
    <div className="space-y-2 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[var(--card-pad)]">
      <div className="flex items-center gap-2">
        <Icon
          className="h-4 w-4"
          style={{ color: "var(--accent)" }}
          aria-hidden="true"
        />
        <div className="text-sm font-semibold">{title}</div>
      </div>
      <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
        {children}
      </p>
    </div>
  );
}

export default function FeedbackSettingsPanel({
  onStartConversation,
}: FeedbackSettingsPanelProps) {
  const [feedbackOptIn, setFeedbackOptIn] = useState(readGuardianFeedbackOptIn);

  function handleOptInChange() {
    const nextValue = !feedbackOptIn;
    setFeedbackOptIn(nextValue);
    writeGuardianFeedbackOptIn(nextValue);
  }

  return (
    <div data-testid="feedback-settings-panel" className="space-y-[var(--shell-gap)]">
      <div className="flex flex-col gap-4 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[var(--card-pad)] md:flex-row md:items-start md:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--tile-radius,19px)]"
            style={{
              background: "color-mix(in srgb, var(--accent) 16%, transparent)",
              color: "var(--accent)",
            }}
          >
            <MessageSquareText className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 space-y-1">
            <div className="text-base font-semibold">Make the rough edges useful</div>
            <p className="max-w-2xl text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
              Tell Guardian what went wrong in the same calm space where the
              work happened. The feedback flow is designed to keep the
              interface quiet and the useful context intact.
            </p>
          </div>
        </div>
        <div
          className="flex shrink-0 items-center gap-2 self-start rounded-full border px-3 py-1.5 text-[11px] font-medium"
          style={{
            borderColor: feedbackOptIn
              ? "color-mix(in srgb, var(--accent) 48%, var(--panel-border))"
              : "var(--panel-border)",
            color: feedbackOptIn ? "var(--accent)" : "var(--muted)",
          }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: feedbackOptIn ? "var(--accent)" : "var(--muted)" }}
            aria-hidden="true"
          />
          {feedbackOptIn ? "Preference saved" : "Off by default"}
        </div>
      </div>

      <div className="grid gap-[var(--radius-micro)] md:grid-cols-3">
        <FeatureNote icon={ShieldCheck} title="You stay in control">
          The planned report flow asks before a report is prepared for
          submission. This setting never grants permission to send anything by
          itself.
        </FeatureNote>
        <FeatureNote icon={Bug} title="Useful context">
          The planned report flow can include relevant conversation and runtime
          details without asking you to copy logs or decode technical jargon.
        </FeatureNote>
        <FeatureNote icon={MessageSquareText} title="Quiet by design">
          Feedback lives here and in Guardian. There is no persistent banner,
          warning strip, or mail link across the workspace.
        </FeatureNote>
      </div>

      <div className="flex flex-col gap-4 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[var(--card-pad)] md:flex-row md:items-center md:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="text-sm font-semibold">Opt in to Guardian report offers</div>
          <p className="max-w-2xl text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
            Save your choice for the report flow. This preview can start a
            Guardian feedback conversation, but automatic report submission is
            not connected yet. You will always be asked before anything leaves
            this workspace.
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={feedbackOptIn}
          aria-label="Opt in to Guardian report offers"
          className="relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border p-1 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          style={{
            borderColor: feedbackOptIn ? "var(--accent)" : "var(--panel-border)",
            background: feedbackOptIn
              ? "color-mix(in srgb, var(--accent) 72%, var(--panel-bg))"
              : "color-mix(in srgb, var(--panel-bg) 82%, var(--muted))",
          }}
          onClick={handleOptInChange}
        >
          <span
            className="h-5 w-5 rounded-full bg-[var(--panel-bg)] shadow-sm transition-transform"
            style={{ transform: feedbackOptIn ? "translateX(20px)" : "translateX(0)" }}
            aria-hidden="true"
          />
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-[var(--tile-radius,19px)] p-[var(--card-pad)] md:flex-row md:items-center md:justify-between" style={{ background: "color-mix(in srgb, var(--accent) 8%, transparent)" }}>
        <div className="space-y-1">
          <div className="text-sm font-semibold">Something not meeting expectations?</div>
          <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
            Start a private Guardian conversation and describe it in your own words.
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          className="shrink-0"
          onClick={onStartConversation}
        >
          Tell Guardian what happened
          <ArrowUpRight className="ml-2 h-3.5 w-3.5" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
