import React, { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import api from "@/lib/api";

import type { ConnectionEntry } from "./connectionCatalog";

type Status = { available: boolean; configured: boolean; state: string; generation?: string; repositories?: string[] };
type Installation = { id: number; account_login: string };
type Repository = { id: number; full_name: string };

/** Browser authorization only. Tokens and callback codes never enter this UI. */
export function KnowledgeOAuthSetup({ connection, onClose, onChanged }: {
  connection: ConnectionEntry; onClose: () => void; onChanged: () => void;
}) {
  const github = connection.id === "github_knowledge";
  const base = `/api/connect/${github ? "github-knowledge" : "notion"}/oauth`;
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [installations, setInstallations] = useState<Installation[]>([]);
  const [installation, setInstallation] = useState<number | null>(null);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const epoch = useRef(0);
  const pending = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const popup = useRef<Window | null>(null);
  function stop() {
    epoch.current += 1;
    pending.current = false;
    clearTimeout(timer.current);
    popup.current?.close();
    popup.current = null;
  }
  useEffect(() => {
    const id = ++epoch.current;
    api.get<Status>(`${base}/status`).then(({ data }) => {
      if (id === epoch.current) setStatus(data);
    }).catch(() => {
      if (id === epoch.current) setMessage("Unable to check connection status.");
    });
    return stop;
  }, [base]);

  async function loadInstallations(id: number) {
    const result = await api.get<{ installations: Installation[] }>(`${base}/installations`);
    if (id === epoch.current) setInstallations(result.data.installations);
  }
  async function authorize() {
    if (pending.current) return;
    stop();
    pending.current = true;
    const id = epoch.current;
    setBusy(true); setMessage("");
    // Open synchronously with the gesture, before the asynchronous start call.
    popup.current = window.open("about:blank", "_blank", "width=600,height=720");
    if (!popup.current) {
      pending.current = false; setBusy(false);
      setMessage("Allow pop-ups for this site and try again."); return;
    }
    popup.current.opener = null;
    try {
      const result = await api.post<{ authorization_url: string; generation: string }>(`${base}/start`, {});
      if (id !== epoch.current) return;
      const url = new URL(result.data.authorization_url);
      const allowed = github ? "github.com" : "api.notion.com";
      if (url.protocol !== "https:" || url.hostname !== allowed || url.username || url.password) throw new Error("Invalid authorization URL");
      popup.current!.location.href = url.href;
      const started = Date.now();
      const poll = async () => {
        if (id !== epoch.current) return;
        try {
          const response = await api.get<Status>(`${base}/status`);
          if (id !== epoch.current) return;
          if (["connected", "needs_scope"].includes(response.data.state) && response.data.generation === result.data.generation) {
            setStatus(response.data); setSelected(response.data.repositories ?? []);
            if (github) await loadInstallations(id);
            if (id !== epoch.current) return;
            stop(); setBusy(false); onChanged();
            setMessage(github ? "Authorized. Select the repositories Codexify may read." : "Connected to the pages you authorized in Notion.");
            return;
          }
        } catch { /* Retry transient status reads, within the bounded window. */ }
        if (id !== epoch.current) return;
        if (popup.current?.closed || Date.now() - started > 300000) {
          stop(); setBusy(false); setMessage("Authorization ended. Check status or try again."); return;
        }
        timer.current = setTimeout(poll, 1500);
      };
      timer.current = setTimeout(poll, 1500);
    } catch {
      if (id !== epoch.current) return;
      stop(); setBusy(false); setMessage("Could not start authorization. Check the provider setup and try again.");
    }
  }
  async function chooseInstallation(value: string) {
    stop(); const id = epoch.current;
    setInstallation(value ? Number(value) : null); setRepositories([]); setSelected([]);
    if (!value) return;
    setBusy(true);
    try {
      const result = await api.get<{ repositories: Repository[]; incomplete?: boolean }>(`${base}/installations/${Number(value)}/repositories`);
      if (id !== epoch.current) return;
      setRepositories(result.data.repositories);
      setMessage(result.data.incomplete ? "Showing a bounded repository list. Only selected repositories will be enabled." : "Select up to 20 repositories.");
    } catch { if (id === epoch.current) setMessage("Unable to load repositories."); }
    finally { if (id === epoch.current) setBusy(false); }
  }
  async function saveRepositories() {
    if (pending.current || !installation || !selected.length) return;
    pending.current = true; setBusy(true); const id = epoch.current;
    try {
      const result = await api.put<Status>(`${base}/repositories`, { installation_id: installation, repositories: selected });
      if (id !== epoch.current) return;
      setStatus(result.data); setMessage("Repository scope saved. Access is read-only."); onChanged();
    } catch { if (id === epoch.current) setMessage("Could not save repository scope."); }
    finally { if (id === epoch.current) { pending.current = false; setBusy(false); } }
  }
  async function disconnect() {
    stop(); const id = epoch.current; pending.current = true; setBusy(true);
    try {
      await api.post(`${base}/disconnect`, {});
      if (id !== epoch.current) return;
      setStatus((old) => ({ available: old?.available ?? false, configured: false, state: "disconnected" }));
      setRepositories([]); setInstallations([]); setSelected([]); setInstallation(null);
      setMessage("Disconnected from Codexify. Manage provider-side authorization in the provider's settings."); onChanged();
    } catch { if (id === epoch.current) setMessage("Could not disconnect. Try again."); }
    finally { if (id === epoch.current) { pending.current = false; setBusy(false); } }
  }
  return <div role="dialog" aria-modal="true" aria-label={`${connection.display_name} setup`} className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div className="bg-background rounded-xl p-6 max-w-xl w-full space-y-4">
      <h2>{connection.display_name}</h2>
      <p>Authorize read-only access in your provider's browser window. Your credentials stay on the server.</p>
      {status?.available === false && <p>OAuth is not configured by this server's operator yet.</p>}
      {status?.configured && <p>Authorization saved. {github && `Allowed repositories: ${(status.repositories ?? []).join(", ") || "none yet"}.`}</p>}
      <Button disabled={busy || !status?.available} onClick={authorize}>{status?.configured ? "Reconnect" : "Connect"} {github ? "GitHub" : "Notion"}</Button>
      {github && (status?.configured || status?.state === "needs_scope") && <Button disabled={busy} onClick={() => { const id = epoch.current; void loadInstallations(id).catch(() => { if (id === epoch.current) setMessage("Unable to load installations."); }); }}>Choose repositories</Button>}
      {installations.length > 0 && <label>GitHub installation<select aria-label="GitHub installation" value={installation ?? ""} disabled={busy} onChange={(event) => void chooseInstallation(event.target.value)}><option value="">Choose an installation</option>{installations.map((item) => <option key={item.id} value={item.id}>{item.account_login}</option>)}</select></label>}
      {repositories.map((repo) => <label className="block" key={repo.id}><input type="checkbox" disabled={busy || (!selected.includes(repo.full_name) && selected.length >= 20)} checked={selected.includes(repo.full_name)} onChange={(event) => setSelected((old) => event.target.checked ? [...old, repo.full_name] : old.filter((name) => name !== repo.full_name))} />{repo.full_name}</label>)}
      {repositories.length > 0 && <Button disabled={busy || !selected.length} onClick={saveRepositories}>Save repository access</Button>}
      {message && <p role="status">{message}</p>}
      {(status?.configured || status?.state === "needs_scope" || busy) && <Button disabled={busy && !popup.current} onClick={disconnect}>Disconnect</Button>}
      <Button variant="ghost" onClick={() => { stop(); onClose(); }}>Close</Button>
      <p className="text-xs">Closing stops this window's checks; it does not revoke an authorization already accepted. Use Disconnect to invalidate a pending connection.</p>
    </div>
  </div>;
}
