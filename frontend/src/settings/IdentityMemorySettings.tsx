import React from "react";
import { fetchIdentitySettings, saveIdentitySettings, IdentitySettings } from "@/imprint/settingsApi";

type Props = {
  userId?: string;
};

export default function IdentityMemorySettings({ userId }: Props) {
  const [settings, setSettings] = React.useState<IdentitySettings | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetchIdentitySettings(userId)
      .then(setSettings)
      .catch((e) => setError(e?.message || "Failed to load settings"));
  }, [userId]);

  const updateField = (field: keyof IdentitySettings, value: any) => {
    if (!settings) return;
    setSettings({ ...settings, [field]: value });
  };

  const onSave = async () => {
    if (!settings) return;
    setSaving(true);
    setError(null);
    try {
      const next = await saveIdentitySettings({ ...settings, user_id: userId });
      setSettings(next);
    } catch (e: any) {
      setError(e?.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border p-4 space-y-4" style={{ borderColor: "var(--panel-border)" }}>
      <div>
        <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          Identity & Memory
        </div>
        <div className="text-xs opacity-70" style={{ color: "var(--muted)" }}>
          Control how the system stores identity traits and diary content.
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs font-semibold" style={{ color: "var(--text)" }}>
          Memory mode
        </div>
        <div className="space-y-2 text-xs" style={{ color: "var(--text)" }}>
          {[
            { value: "none", label: "No identity memory", helper: "Skip all identity storage." },
            { value: "light", label: "Light imprint (recommended)", helper: "Store tone/style and interaction habits." },
            { value: "deep", label: "Deep identity (advanced)", helper: "Full identity modeling (non-sensitive)." },
          ].map((opt) => (
            <label key={opt.value} className="flex items-start gap-2 cursor-pointer">
              <input
                type="radio"
                name="memory_mode"
                value={opt.value}
                checked={settings?.memory_mode === opt.value}
                onChange={() => updateField("memory_mode", opt.value as IdentitySettings["memory_mode"])}
              />
              <span>
                <div className="font-semibold">{opt.label}</div>
                <div className="opacity-70">{opt.helper}</div>
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between text-xs">
        <div>
          <div className="font-semibold" style={{ color: "var(--text)" }}>
            Allow sensitive modeling
          </div>
          <div className="opacity-70" style={{ color: "var(--muted)" }}>
            Permit modeling of sensitive traits (diagnoses, politics).
          </div>
        </div>
        <input
          type="checkbox"
          checked={settings?.allow_sensitive_modeling || false}
          onChange={(e) => updateField("allow_sensitive_modeling", e.target.checked)}
        />
      </div>

      <div className="flex items-center justify-between text-xs">
        <div>
          <div className="font-semibold" style={{ color: "var(--text)" }}>
            Require unlock for diary threads
          </div>
          <div className="opacity-70" style={{ color: "var(--muted)" }}>
            Prevent identity writes from diary threads unless explicitly unlocked.
          </div>
        </div>
        <input
          type="checkbox"
          checked={settings?.diary_requires_unlock || false}
          onChange={(e) => updateField("diary_requires_unlock", e.target.checked)}
        />
      </div>

      {error && (
        <div className="text-xs text-red-400" role="alert">
          {error}
        </div>
      )}
      <div className="flex justify-end">
        <button className="embedded-btn" onClick={onSave} disabled={saving || !settings}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
