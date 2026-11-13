import React, { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { getAuthState, subscribeAuthState } from "@/lib/authState";
import { parseUiArtifacts, type GenerativeUiArtifact } from "@/features/chat/components/generativeUi/artifactCodec";
import GenerativeUIRenderer from "@/features/chat/components/generativeUi/GenerativeUIRenderer";

type Widget = { widget_id: string; name: string; current_revision: number };
const url = (path = "") => "/api/saved-widgets" + path;
const failure = (error: any, saving = false) => error?.response?.status === 422
  ? "This artifact is not eligible to save. It must be a self-contained interactive widget from a completed Guardian response."
  : error?.response?.status === 409
    ? "This widget changed. Close this form and refresh before saving a new version."
    : saving ? "The save did not complete. Check Library before retrying to avoid creating a duplicate."
      : "Widgets could not be loaded. Check your connection and sign-in, then try again.";

export function SavedWidgetLibrary() {
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [selection, setSelection] = useState<Widget | null>(null);
  const [revisions, setRevisions] = useState<number[]>([]);
  const [revision, setRevision] = useState(1);
  const [artifact, setArtifact] = useState<GenerativeUiArtifact | null>(null);
  const generation = useRef(0);
  const launchGeneration = useRef(0);
  async function load(offset = 0) {
    const current = ++generation.current;
    setBusy(true); setError("");
    try {
      const { data } = await api.get(url(), { params: { limit: 50, offset } });
      if (current !== generation.current) return;
      if (!Array.isArray(data.widgets) || data.count !== data.widgets.length) throw new Error();
      setWidgets(previous => [...new Map((offset ? [...previous, ...data.widgets] : data.widgets).map((w: Widget) => [w.widget_id, w])).values()] as Widget[]);
      setNext(data.next_offset);
    } catch (e) { if (current === generation.current) setError(failure(e)); }
    finally { if (current === generation.current) setBusy(false); }
  }
  useEffect(() => {
    void load();
    const refresh = () => { void load(); };
    window.addEventListener("saved-widget-changed", refresh);
    return () => { generation.current++; launchGeneration.current++; window.removeEventListener("saved-widget-changed", refresh); };
  }, []);
  useEffect(() => subscribeAuthState(() => {
    generation.current++; launchGeneration.current++;
    setWidgets([]); setNext(null); setSelection(null); setArtifact(null); setBusy(false);
    setError("Account changed. Refresh to load this account’s widgets.");
  }), []);
  async function select(widget: Widget) {
    const current = ++launchGeneration.current;
    setSelection(widget); setRevision(widget.current_revision); setArtifact(null); setRevisions([]); setError(""); setBusy(false);
    try {
      const { data } = await api.get(url("/" + encodeURIComponent(widget.widget_id)));
      if (current !== launchGeneration.current) return;
      if (data.source_withheld) throw new Error();
      setRevisions(data.revisions.map((r: { revision: number }) => r.revision));
    } catch(e) { if (current === launchGeneration.current) { setError(failure(e)); setSelection(null); } }
  }
  async function launch() {
    if (!selection) return;
    const current = ++launchGeneration.current;
    setArtifact(null); setError(""); setBusy(true);
    try {
      const { data } = await api.get(url("/" + encodeURIComponent(selection.widget_id) + "/revisions/" + revision));
      if (current !== launchGeneration.current) return;
      const raw = data.artifact_snapshot;
      if (data.widget_id !== selection.widget_id || data.revision !== revision) throw new Error();
      const parsed = raw && parseUiArtifacts("<!-- cfy-ui:" + encodeURIComponent(JSON.stringify(raw)) + " -->").artifacts[0];
      if (!parsed || parsed.kind !== "sandbox") throw new Error();
      setArtifact(parsed);
    } catch(e) { if (current === launchGeneration.current) setError(failure(e)); }
    finally { if (current === launchGeneration.current) setBusy(false); }
  }
  return <section className="flex flex-col gap-3 overflow-auto p-2" aria-label="Saved widgets">
    <header className="flex items-center justify-between"><h2>Saved widgets</h2><button disabled={busy} onClick={() => void load()}>Refresh</button></header>
    <p className="text-xs opacity-70">Your account’s widgets. Launch independently; each launch starts fresh.</p>
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">Loading…</p>}
    {!busy && !error && widgets.length === 0 && <p>No saved widgets yet. Use Save in a Guardian response.</p>}
    {widgets.map(widget => <button key={widget.widget_id} className="rounded-xl border p-3 text-left" onClick={() => void select(widget)}>
      {widget.name} · Version {widget.current_revision}
    </button>)}
    {next != null && <button disabled={busy} onClick={() => void load(next)}>Load more widgets</button>}
    {selection && <section className="rounded-xl border p-3" aria-label={selection.name}>
      <header className="flex justify-between"><h3>{selection.name}</h3><button onClick={() => { launchGeneration.current++; setSelection(null); setArtifact(null); setBusy(false); }}>Close widget</button></header>
      <label>Version <select value={revision} onChange={e => { launchGeneration.current++; setRevision(Number(e.target.value)); setArtifact(null); setBusy(false); }}>
        {(revisions.length ? revisions : [selection.current_revision]).map(r => <option key={r} value={r}>{r}</option>)}
      </select></label>
      <button disabled={busy || !!artifact} onClick={() => void launch()}>Launch widget</button>
      {artifact && <GenerativeUIRenderer key={selection.widget_id + ":" + revision} artifacts={[artifact]} />}
    </section>}
  </section>;
}

function SaveWidget({ threadId, messageId, index, title }: { threadId: number; messageId: number; index: number; title: string }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(title || "My widget");
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => subscribeAuthState(() => { setOpen(false); setWidgets([]); setNext(null); setNotice(""); }), []);
  async function begin() {
    setOpen(true); setNotice(""); setTarget(""); setWidgets([]);
    try {
      // One bounded page: never silently choose an unseen widget.
      const { data } = await api.get(url(), { params: { limit: 100 } });
      if (!Array.isArray(data.widgets) || data.count !== data.widgets.length) throw new Error();
      if (alive.current) { setWidgets(data.widgets); setNext(data.next_offset); }
    } catch { if (alive.current) setNotice("Existing widgets could not be loaded. Saving as new is still available."); }
  }
  async function save() {
    const account = getAuthState();
    setBusy(true); setNotice("");
    try {
      const selected = widgets.find(w => w.widget_id === target);
      const coordinates = { thread_id: threadId, message_id: messageId, artifact_index: index };
      const { data } = selected
        ? await api.post(url("/" + encodeURIComponent(selected.widget_id) + "/revisions"), { ...coordinates, base_revision: selected.current_revision })
        : await api.post(url(), { ...coordinates, name: name.trim() });
      if (!alive.current || account !== getAuthState()) return;
      setNotice("Saved version " + data.revision + " to Library."); setOpen(false);
      window.dispatchEvent(new Event("saved-widget-changed"));
    } catch(e) { if (alive.current) setNotice(failure(e, true)); }
    finally { if (alive.current) setBusy(false); }
  }
  return <div className="rounded-xl border p-2">
    {!open && <button onClick={() => void begin()}>Save {title || "widget"} to Library</button>}
    {open && <div className="flex flex-wrap gap-2">
      <label>Save as <select value={target} disabled={busy} onChange={e => setTarget(e.target.value)}>
        <option value="">New widget / separate copy</option>
        {widgets.map(w => <option key={w.widget_id} value={w.widget_id}>{w.name} — new version after {w.current_revision}</option>)}
      </select></label>
      {!target && <input aria-label="Widget name" maxLength={255} value={name} disabled={busy} onChange={e => setName(e.target.value)} />}
      <button disabled={busy || (!target && !name.trim())} onClick={() => void save()}>{busy ? "Saving…" : target ? "Save new version" : "Save as new"}</button>
      <button disabled={busy} onClick={() => setOpen(false)}>Cancel</button>
    </div>}
    {open && next != null && <button disabled={busy} onClick={async () => {
      const account = getAuthState();
      try { const { data } = await api.get(url(), { params: { limit: 100, offset: next } });
        if (alive.current && account === getAuthState() && Array.isArray(data.widgets)) { setWidgets(prior => [...prior, ...data.widgets]); setNext(data.next_offset); }
      } catch { setNotice("More widgets could not be loaded. Try again."); }
    }}>Load more widgets</button>}
    {notice && <p role="status">{notice}</p>}
  </div>;
}
export function SaveWidgetControls({ content, threadId, messageId }: { content: string; threadId?: number; messageId: string }) {
  const id = Number(messageId);
  if (!threadId || !Number.isSafeInteger(id) || id <= 0) return null;
  return <>{[...content.matchAll(/<!--\s*cfy-ui:(.*?)-->/gis)].map((match, index) => {
    const artifact = parseUiArtifacts(match[0]).artifacts[0];
    return artifact?.kind === "sandbox" ? <SaveWidget key={index} threadId={threadId} messageId={id} index={index} title={artifact.title || ""} /> : null;
  })}</>;
}

