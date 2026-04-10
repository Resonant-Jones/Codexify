import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import SettingsSectionCard from "@/features/settings/components/SettingsSectionCard";
import usePersonaSettings from "@/features/settings/hooks/usePersonaSettings";

type PersonalFactsPanelProps = {
  className?: string;
  projectId?: number | null;
  threadId?: number;
};

export default function PersonalFactsPanel({
  className,
  projectId,
  threadId,
}: PersonalFactsPanelProps) {
  const {
    draftText,
    error,
    hasLoaded,
    isDirty,
    isEmptySaveBlocked,
    loading,
    persona,
    reset,
    reload,
    save,
    saving,
    setDraftText,
  } = usePersonaSettings({ projectId, threadId });

  const secondaryActionLabel = isDirty ? "Reset" : "Reload";
  const secondaryAction = isDirty ? reset : () => void reload();
  const saveDisabled = loading || saving || !isDirty || isEmptySaveBlocked;

  return (
    <SettingsSectionCard
      data-testid="personal-facts-panel"
      className={[
        "space-y-4",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="space-y-1">
        <h2 className="text-base font-semibold" style={{ color: "var(--text)" }}>
          Persona
        </h2>
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Persona is the user-editable voice or mask layer. It shapes tone and
          style without changing deeper identity.
        </p>
      </div>

      {loading ? (
        <div
          className="rounded-xl border px-3 py-4 text-sm"
          style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
          role="status"
        >
          Loading active persona…
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3 text-xs">
            <span style={{ color: "var(--muted)" }}>
              Edit the active persona text for this project and user context
              only.
            </span>
            <span style={{ color: "var(--muted)" }}>{draftText.length} chars</span>
          </div>

          <label className="block space-y-2" htmlFor="persona-settings-text">
            <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
              Active persona text
            </span>
            <Textarea
              id="persona-settings-text"
              value={draftText}
              onChange={(event) => setDraftText(event.target.value)}
              rows={10}
              disabled={saving}
              placeholder="Describe the voice or stance Guardian should use here."
              aria-describedby="persona-settings-help"
            />
          </label>

          <p
            className="text-xs leading-5"
            id="persona-settings-help"
            style={{ color: "var(--muted)" }}
          >
            {persona?.canClear
              ? "Clearing is enabled for this context, so an empty save will remove the active persona text."
              : "Empty saves are blocked unless the backend explicitly enables clearing for this context."}
          </p>
        </div>
      )}

      {isDirty && isEmptySaveBlocked && hasLoaded && (
        <div
          className="rounded-xl border px-3 py-2 text-sm"
          style={{
            borderColor: "rgba(234, 179, 8, 0.35)",
            background: "rgba(234, 179, 8, 0.12)",
            color: "var(--text)",
          }}
          role="note"
        >
          Add persona text before saving. Clearing is not enabled here.
        </div>
      )}

      {error && (
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
      )}

      <div className="flex items-center justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          className="border border-[var(--panel-border)]"
          onClick={secondaryAction}
          disabled={loading || saving}
        >
          {secondaryActionLabel}
        </Button>
        <Button type="button" onClick={() => void save()} disabled={saveDisabled}>
          {saving ? "Saving…" : "Save Persona"}
        </Button>
      </div>
    </SettingsSectionCard>
  );
}
