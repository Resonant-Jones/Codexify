import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { fetchRetainedPdfAudit, identifyRetainedPdf, repairRetainedPdf,
  type AccountImportJob, type RetainedPdfIdentity, type RetainedPdfAudit } from "@/lib/api";

export default function RetainedPdfRepair({ job }: { job: AccountImportJob }) {
  const input = useRef<HTMLInputElement>(null);
  const active = useRef<AbortController | null>(null);
  const submitting = useRef(false);
  const [identity, setIdentity] = useState<RetainedPdfIdentity | null>(null);
  const [working, setWorking] = useState(false);
  const [sent, setSent] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => () => { active.current?.abort(); }, []);

  function showAudit(audit: RetainedPdfAudit, selected = identity) {
    if (audit.job.job_id !== job.job_id) throw new Error("Unexpected repair receipt");
    const completed = [...audit.events].reverse().find(event => event.path === selected?.relative_path &&
      event.sha256 === selected?.file_sha256 && event.completed_at);
    setMessage(completed ? `Retained PDF repaired. Original bytes verified; ${completed.text_extracted ? "text available" : "text unavailable"}. Original warning history is preserved.` :
      audit.busy ? "Repair is still running. Check its status again." :
      "No completed repair receipt for this selection. Keep the original file and check status before submitting again.");
  }

  async function select(file?: File) {
    if (!file || submitting.current) return;
    active.current?.abort();
    const controller = new AbortController(); active.current = controller;
    setIdentity(null); setSent(false); setWorking(true); setMessage("Verifying the selected original PDF...");
    try {
      const selected = await identifyRetainedPdf(job, file, controller.signal);
      if (!controller.signal.aborted) { setIdentity(selected); setMessage("Original PDF matches the retained import. Ready to repair."); }
    } catch {
      if (!controller.signal.aborted) setMessage("Selection did not verify. Choose the exact original PDF from this export (up to 16 MiB); ambiguous matches cannot be repaired here.");
    } finally { if (!controller.signal.aborted) setWorking(false); }
  }

  async function submit() {
    if (!identity || submitting.current || sent) return;
    submitting.current = true; setSent(true); setWorking(true);
    setMessage("Verifying retained bytes and repairing the PDF. You can check the saved status if this request times out.");
    try { showAudit(await repairRetainedPdf(job.job_id, identity)); }
    catch { setMessage("The request outcome is uncertain. Check repair status before any further submission."); }
    finally { submitting.current = false; setWorking(false); }
  }

  async function check() {
    if (working) return;
    setWorking(true);
    try { showAudit(await fetchRetainedPdfAudit(job.job_id)); }
    catch { setMessage("Repair status is unavailable. Keep the original PDF and check again later."); }
    finally { setWorking(false); }
  }

  return <div className="mt-3 border-t pt-3 space-y-2">
    <div className="font-medium">Repair a retained PDF</div>
    <p className="text-xs opacity-80">Select the original PDF to verify its identity. The repair uses the retained bytes under this completed import.</p>
    <input ref={input} type="file" accept=".pdf,.dat,application/pdf,application/octet-stream" className="hidden"
      aria-label="Original PDF for retained repair" onChange={event => { const file = event.target.files?.[0]; event.target.value = ""; void select(file); }} />
    <div className="flex flex-wrap gap-2">
      <Button type="button" variant="outline" disabled={working} onClick={() => input.current?.click()}>Select retained PDF</Button>
      <Button type="button" disabled={working || !identity || sent} onClick={() => void submit()}>Repair retained PDF</Button>
      <Button type="button" variant="outline" disabled={working} onClick={() => void check()}>Check repair status</Button>
    </div>
    {message && <p role="status" className="text-xs">{message}</p>}
  </div>;
}
