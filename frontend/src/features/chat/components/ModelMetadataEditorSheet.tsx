import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import api, { buildLlmModelOverridePath } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { LlmCatalogModel } from "@/features/chat/hooks/useLlmCatalog";

type ModelMetadataEditorSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  providerId: string | null | undefined;
  model: LlmCatalogModel | null | undefined;
  onSaved?: () => Promise<void> | void;
};

function normalizeLabel(value: string): string {
  return value.trim();
}

export function ModelMetadataEditorSheet({
  open,
  onOpenChange,
  providerId,
  model,
  onSaved,
}: ModelMetadataEditorSheetProps) {
  const [displayLabel, setDisplayLabel] = useState("");
  const [pickerLabel, setPickerLabel] = useState("");
  const [supportsVision, setSupportsVision] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialValuesRef = useRef({
    displayLabel: "",
    pickerLabel: "",
    supportsVision: false,
  });

  const hasOverride = Boolean(model?.override);
  const modelTitle = useMemo(
    () =>
      model?.displayLabel ??
      model?.pickerLabel ??
      model?.displayName ??
      model?.canonicalId ??
      "Model",
    [model]
  );

  useEffect(() => {
    if (!open || !model) return;
    setDisplayLabel(
      model.override?.displayLabel ??
        model.displayLabel ??
        model.pickerLabel ??
        model.canonicalId
    );
    setPickerLabel(
      model.override?.pickerLabel ??
        model.pickerLabel ??
        model.displayLabel ??
        model.canonicalId
    );
    setSupportsVision(
      model.override?.supportsVision ?? model.supportsVision ?? false
    );
    initialValuesRef.current = {
      displayLabel: model.override?.displayLabel ??
        model.displayLabel ??
        model.pickerLabel ??
        model.canonicalId,
      pickerLabel: model.override?.pickerLabel ??
        model.pickerLabel ??
        model.displayLabel ??
        model.canonicalId,
      supportsVision:
        model.override?.supportsVision ?? model.supportsVision ?? false,
    };
    setError(null);
  }, [model, open]);

  const close = () => {
    if (!saving) {
      onOpenChange(false);
    }
  };

  const save = async () => {
    if (!providerId || !model?.canonicalId) {
      setError("Select a model before editing metadata.");
      return;
    }

    const nextDisplayLabel = normalizeLabel(displayLabel);
    const nextPickerLabel = normalizeLabel(pickerLabel);
    const payload: Record<string, unknown> = {};
    if (nextDisplayLabel !== initialValuesRef.current.displayLabel) {
      payload.display_label = nextDisplayLabel || null;
    }
    if (nextPickerLabel !== initialValuesRef.current.pickerLabel) {
      payload.picker_label = nextPickerLabel || null;
    }
    if (supportsVision !== initialValuesRef.current.supportsVision) {
      payload.supports_vision = supportsVision;
    }

    if (Object.keys(payload).length === 0) {
      onOpenChange(false);
      return;
    }

    if (
      payload.display_label === null &&
      payload.picker_label === null &&
      !Object.prototype.hasOwnProperty.call(payload, "supports_vision")
    ) {
      await reset();
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await api.put(buildLlmModelOverridePath(providerId, model.canonicalId), payload);
      await onSaved?.();
      window.dispatchEvent(
        new CustomEvent("cfy:toast", {
          detail: { kind: "success", message: `Saved metadata for ${modelTitle}.` },
        })
      );
      onOpenChange(false);
    } catch (err: any) {
      const message =
        typeof err?.response?.data?.detail === "string"
          ? err.response.data.detail
          : typeof err?.message === "string"
            ? err.message
            : "Failed to save model metadata.";
      setError(message);
      window.dispatchEvent(
        new CustomEvent("cfy:toast", {
          detail: { kind: "error", message },
        })
      );
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    if (!providerId || !model?.canonicalId) return;
    setSaving(true);
    setError(null);
    try {
      await api.delete(buildLlmModelOverridePath(providerId, model.canonicalId));
      await onSaved?.();
      window.dispatchEvent(
        new CustomEvent("cfy:toast", {
          detail: { kind: "success", message: `Reset metadata for ${modelTitle}.` },
        })
      );
      onOpenChange(false);
    } catch (err: any) {
      const message =
        typeof err?.response?.data?.detail === "string"
          ? err.response.data.detail
          : typeof err?.message === "string"
            ? err.message
            : "Failed to reset model metadata.";
      setError(message);
      window.dispatchEvent(
        new CustomEvent("cfy:toast", {
          detail: { kind: "error", message },
        })
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[min(92vw,34rem)] overflow-y-auto">
        <div className="flex h-full flex-col">
          <SheetHeader className="space-y-2">
            <SheetTitle className="text-base">Edit model metadata</SheetTitle>
            <div className="text-sm" style={{ color: "var(--muted)" }}>
              Adjust the visible labels or correct a wrong vision tag. The backend id stays
              {` `}
              <span className="font-mono text-[11px]" style={{ color: "var(--text)" }}>
                {model?.canonicalId ?? "unchanged"}
              </span>
              {hasOverride ? " · manual override active" : " · no manual override yet"}
            </div>
          </SheetHeader>

          <div className="flex-1 space-y-4 p-4">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.14em]" style={{ color: "var(--muted)" }}>
                Display label
              </label>
              <Input
                value={displayLabel}
                onChange={(e) => setDisplayLabel(e.target.value)}
                placeholder="What the selector should show"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.14em]" style={{ color: "var(--muted)" }}>
                Picker label
              </label>
              <Input
                value={pickerLabel}
                onChange={(e) => setPickerLabel(e.target.value)}
                placeholder="Optional secondary label"
              />
            </div>

            <label
              className={cn(
                "flex items-center gap-3 rounded-2xl border px-3 py-3",
                "border-[color-mix(in_oklab,var(--panel-border)_84%,var(--text)_16%)]"
              )}
            >
              <input
                type="checkbox"
                checked={supportsVision}
                onChange={(e) => setSupportsVision(e.target.checked)}
                className="h-4 w-4"
              />
              <span className="min-w-0">
                <span className="block text-sm font-medium" style={{ color: "var(--text)" }}>
                  Vision capable
                </span>
                <span className="block text-xs" style={{ color: "var(--muted)" }}>
                  Allow images and other visual attachments to route to this model.
                </span>
              </span>
            </label>

            {error ? (
              <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                {error}
              </div>
            ) : null}
          </div>

          <div className="flex items-center justify-between gap-3 border-t border-[color-mix(in_oklab,var(--panel-border)_84%,var(--text)_16%)] p-4">
            <Button
              type="button"
              variant="ghost"
              onClick={reset}
              disabled={saving || !model?.canonicalId}
            >
              Reset to defaults
            </Button>
            <div className="flex items-center gap-2">
              <Button type="button" variant="ghost" onClick={close} disabled={saving}>
                Cancel
              </Button>
              <Button type="button" onClick={save} disabled={saving || !model?.canonicalId || !providerId}>
                {saving ? "Saving…" : "Save"}
              </Button>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export default ModelMetadataEditorSheet;
