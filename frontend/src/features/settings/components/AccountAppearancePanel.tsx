import { useEffect, useRef, useState } from "react";
import { accountPresentation, useAccountPresentation } from "../accountPresentation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function AccountAppearancePanel() {
  const profile = useAccountPresentation();
  const [draft, setDraft] = useState("");
  const [dirty, setDirty] = useState(false);
  const epoch = useRef(profile.epoch);
  useEffect(() => {
    if (epoch.current !== profile.epoch || !dirty) {
      setDraft(profile.greetingName ?? ""); setDirty(false); epoch.current = profile.epoch;
    }
  }, [profile.epoch, profile.greetingName, dirty]);
  async function save(value: string | null) {
    if (epoch.current !== profile.epoch) return;
    const saved = await accountPresentation.saveGreeting(value, profile.epoch);
    if (saved && epoch.current === profile.epoch) { setDraft(value?.trim() ?? ""); setDirty(false); }
  }
  return <section className="space-y-3 rounded-[var(--tile-radius,19px)] border border-[var(--panel-border)] p-[var(--card-pad)]" aria-label="Account profile and appearance">
    <h3 className="text-sm font-medium">Your profile</h3>
    <p className="text-xs" style={{ color: "var(--muted)" }}>Your greeting and appearance follow your account across Web and Scout. Leave the greeting name empty for a neutral welcome.</p>
    <label className="block text-sm" htmlFor="account-greeting-name">Greeting name</label>
    <Input id="account-greeting-name" value={draft} maxLength={255} disabled={!profile.ready || profile.saving}
      autoComplete="off" onChange={(e) => { setDraft(e.target.value); setDirty(true); }} />
    <div className="flex gap-2">
      <Button type="button" disabled={!profile.ready || profile.saving || !dirty} onClick={() => void save(draft)}>Save greeting</Button>
      <Button type="button" variant="ghost" disabled={!profile.ready || profile.saving || (!profile.greetingName && !draft)} onClick={() => void save(null)}>Use neutral greeting</Button>
    </div>
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={profile.workspaceUnique} disabled={!profile.ready || profile.saving}
        onChange={(e) => void accountPresentation.setWorkspaceUnique(e.target.checked, profile.epoch)} />
      Keep this workspace’s appearance unique
    </label>
    <p className="text-xs" style={{ color: "var(--muted)" }}>{profile.workspaceUnique ? "Appearance changes stay with this workspace. Your greeting still follows your account." : "Wallpaper, theme, accent and materials are shared with your account."}</p>
    {profile.error ? <div role="alert" className="text-sm">{profile.error} <Button type="button" variant="ghost" onClick={() => accountPresentation.retry()}>Retry</Button></div>
      : <p role="status" className="text-xs" style={{ color: "var(--muted)" }}>{profile.saving ? "Saving…" : profile.ready ? "Saved to your account." : "Sign in to load your profile and appearance."}</p>}
  </section>;
}
