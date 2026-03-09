import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import {
  GUARDIAN_CRON_CUSTOM_SCHEDULE,
  SUPPORTED_GUARDIAN_CRON_PRESETS,
} from "@/features/chat/api/cron";
import useGuardianScheduleAction from "@/features/chat/hooks/useGuardianScheduleAction";

type GuardianScheduleActionProps = {
  className?: string;
};

export default function GuardianScheduleAction({
  className,
}: GuardianScheduleActionProps) {
  const {
    cancelReview,
    confirmCreation,
    createdJob,
    error,
    form,
    isSubmitting,
    review,
    setField,
    submit,
    validationErrors,
  } = useGuardianScheduleAction();

  const targetLabel =
    form.jobType === "webhook" ? "Webhook URL" : "Payload reference";
  const targetHelper =
    form.jobType === "webhook"
      ? "Use a public http(s) endpoint allowed by current cron webhook policy."
      : "Reference the durable action payload or external reference this job should carry.";

  return (
    <section
      className={[
        "space-y-4 rounded-2xl border p-4 sm:p-5",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 88%, transparent)",
        borderColor: "var(--panel-border)",
      }}
      data-testid="guardian-schedule-action"
    >
      <div className="space-y-1">
        <h2 className="text-base font-semibold" style={{ color: "var(--text)" }}>
          Guardian Scheduling
        </h2>
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Create a durable cron job from explicit input. This control stays
          structured on purpose and submits directly to the existing cron API.
        </p>
      </div>

      <div
        className="rounded-xl border px-3 py-2 text-sm"
        style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
      >
        Creating a job here writes a durable scheduled record. Execution still
        depends on the scheduler and cron worker path being available.
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="block space-y-2">
          <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
            Job name
          </span>
          <label htmlFor="guardian-cron-name" className="sr-only">
            Job name
          </label>
          <Input
            id="guardian-cron-name"
            value={form.name}
            onChange={(event) => setField("name", event.target.value)}
            placeholder="Daily status pulse"
            aria-invalid={validationErrors.name ? "true" : "false"}
          />
          {validationErrors.name ? (
            <span className="text-xs text-red-300">{validationErrors.name}</span>
          ) : null}
        </div>

        <div className="block space-y-2">
          <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
            Job type
          </span>
          <label htmlFor="guardian-cron-job-type" className="sr-only">
            Job type
          </label>
          <select
            id="guardian-cron-job-type"
            className="h-9 w-full rounded-md border border-[var(--panel-border)] bg-[var(--panel-bg)]/80 px-3 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            value={form.jobType}
            onChange={(event) =>
              setField("jobType", event.target.value as "noop" | "webhook")
            }
          >
            <option value="noop">No-op</option>
            <option value="webhook">Webhook</option>
          </select>
        </div>

        <div className="block space-y-2">
          <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
            Schedule
          </span>
          <label htmlFor="guardian-cron-schedule" className="sr-only">
            Schedule
          </label>
          <select
            id="guardian-cron-schedule"
            className="h-9 w-full rounded-md border border-[var(--panel-border)] bg-[var(--panel-bg)]/80 px-3 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            value={form.schedulePreset}
            onChange={(event) =>
              setField(
                "schedulePreset",
                event.target.value as
                  | typeof GUARDIAN_CRON_CUSTOM_SCHEDULE
                  | (typeof SUPPORTED_GUARDIAN_CRON_PRESETS)[number]
              )
            }
            aria-invalid={validationErrors.schedule ? "true" : "false"}
          >
            {SUPPORTED_GUARDIAN_CRON_PRESETS.map((preset) => (
              <option key={preset} value={preset}>
                {preset}
              </option>
            ))}
            <option value={GUARDIAN_CRON_CUSTOM_SCHEDULE}>Custom interval</option>
          </select>
          {form.schedulePreset === GUARDIAN_CRON_CUSTOM_SCHEDULE ? (
            <>
              <label
                htmlFor="guardian-cron-custom-schedule"
                className="sr-only"
              >
                Custom schedule expression
              </label>
              <Input
                id="guardian-cron-custom-schedule"
                value={form.customSchedule}
                onChange={(event) =>
                  setField("customSchedule", event.target.value)
                }
                placeholder="*/15 * * * *"
                aria-label="Custom schedule expression"
                aria-invalid={validationErrors.schedule ? "true" : "false"}
              />
            </>
          ) : (
            <div className="text-xs opacity-80" style={{ color: "var(--muted)" }}>
              Presets match the cron backend contract exactly.
            </div>
          )}
          {validationErrors.schedule ? (
            <span className="text-xs text-red-300">
              {validationErrors.schedule}
            </span>
          ) : null}
        </div>

        <div className="block space-y-2">
          <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
            {targetLabel}
          </span>
          <label htmlFor="guardian-cron-target" className="sr-only">
            {targetLabel}
          </label>
          <Input
            id="guardian-cron-target"
            value={form.targetReference}
            onChange={(event) => setField("targetReference", event.target.value)}
            placeholder={
              form.jobType === "webhook"
                ? "https://api.example.com/hook"
                : "status/daily-pulse"
            }
            aria-invalid={validationErrors.targetReference ? "true" : "false"}
          />
          <span className="text-xs opacity-80" style={{ color: "var(--muted)" }}>
            {targetHelper}
          </span>
          {validationErrors.targetReference ? (
            <span className="text-xs text-red-300">
              {validationErrors.targetReference}
            </span>
          ) : null}
        </div>
      </div>

      <label
        className="flex items-center justify-between gap-3 rounded-xl border px-3 py-2"
        style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
      >
        <span className="text-sm">Enable job on create</span>
        <input
          type="checkbox"
          checked={form.isEnabled}
          onChange={(event) => setField("isEnabled", event.target.checked)}
        />
      </label>

      {review ? (
        <div
          className="space-y-3 rounded-xl border p-3"
          style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
        >
          <div className="text-sm font-semibold">Confirm scheduled job</div>
          <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
            Review the durable cron job definition before creating it.
          </p>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            {review.summary.map((item) => (
              <div key={item.label} className="rounded-lg border px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
                <dt className="text-xs uppercase tracking-wide opacity-70">
                  {item.label}
                </dt>
                <dd className="mt-1 break-all">{item.value}</dd>
              </div>
            ))}
          </dl>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              className="border border-[var(--panel-border)]"
              onClick={cancelReview}
              disabled={isSubmitting}
            >
              Edit details
            </Button>
            <Button
              type="button"
              onClick={() => void submit()}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Creating…" : "Create durable job"}
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex justify-end">
          <Button
            type="button"
            onClick={() => void confirmCreation()}
            disabled={isSubmitting}
          >
            Review job
          </Button>
        </div>
      )}

      {createdJob ? (
        <div
          className="rounded-xl border px-3 py-2 text-sm"
          style={{
            borderColor: "rgba(34, 197, 94, 0.35)",
            background: "rgba(34, 197, 94, 0.12)",
            color: "var(--text)",
          }}
          role="status"
        >
          Created durable job #{createdJob.id} for schedule {createdJob.schedule}.
        </div>
      ) : null}

      {error ? (
        <div
          className="rounded-xl border px-3 py-2 text-sm"
          style={{
            borderColor: "rgba(239, 68, 68, 0.35)",
            background: "rgba(239, 68, 68, 0.12)",
            color: "var(--text)",
          }}
          role="alert"
        >
          {error}
        </div>
      ) : null}
    </section>
  );
}
