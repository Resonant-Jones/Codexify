import { webcrypto, createHash } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import api, { identifyRetainedPdf, repairRetainedPdf, fetchRetainedPdfAudit, ACCOUNT_IMPORT_HASH_STEP_TIMEOUT_MS, type AccountImportJob } from "@/lib/api";

const bytes = new TextEncoder().encode("%PDF-original");
const sha = createHash("sha256").update(bytes).digest("hex");
const job = { job_id:"original-job", source_system:"openai", status:"completed_with_warnings", source_export_fingerprint:"b".repeat(64) } as AccountImportJob;
function file() {
  const arrayBuffer=vi.fn(async()=>bytes.buffer.slice(0));
  return { name:"original.dat", size:bytes.length, arrayBuffer,
    slice:()=>({arrayBuffer:async()=>bytes.slice(0,5).buffer}) } as unknown as File;
}
function manifest(count=1) { return {data:{job_id:job.job_id,source_system:"openai",status:job.status,
  files:Array.from({length:count},(_,i)=>({path:`export${i}/original.dat`,size:bytes.length,sha256:sha}))}}; }
beforeEach(()=>vi.stubGlobal("crypto",webcrypto));
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();vi.useRealTimers();});

it("matches exactly one original path/size/hash and POSTs identity only with finite auth transport",async()=>{
  vi.spyOn(api,"get").mockResolvedValue(manifest());
  const post=vi.spyOn(api,"post").mockResolvedValue({data:{events:[]}});
  const identity=await identifyRetainedPdf(job,file());
  expect(identity).toEqual({relative_path:"export0/original.dat",file_size:bytes.length,file_sha256:sha,source_export_fingerprint:job.source_export_fingerprint});
  await repairRetainedPdf(job.job_id,identity);
  expect(post).toHaveBeenCalledExactlyOnceWith("/api/imports/openai-account/original-job/pdf-repair",identity,
    expect.objectContaining({timeout:360000,__cfyDurableAccountImport:true}));
});
it.each([0,2])("refuses %i matches without POSTing",async count=>{
  vi.spyOn(api,"get").mockResolvedValue(manifest(count));const post=vi.spyOn(api,"post");
  await expect(identifyRetainedPdf(job,file())).rejects.toThrow(/exactly one/);expect(post).not.toHaveBeenCalled();
});
it("a late hash after timeout cannot fetch manifest or trigger a repair",async()=>{
  vi.useFakeTimers(); const selected=file(); let finish!:(bytes:ArrayBuffer)=>void;
  vi.spyOn(selected,"arrayBuffer").mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const get=vi.spyOn(api,"get");const post=vi.spyOn(api,"post");
  const attempt=identifyRetainedPdf(job,selected);const rejected=expect(attempt).rejects.toThrow(/verification/);
  await vi.advanceTimersByTimeAsync(ACCOUNT_IMPORT_HASH_STEP_TIMEOUT_MS+1);await rejected;
  finish(bytes.buffer);await Promise.resolve();await Promise.resolve();expect(get).not.toHaveBeenCalled();expect(post).not.toHaveBeenCalled();
});
it("an aborted selection stays cancelled after a native read resolves",async()=>{
  const selected=file();let finish!:(bytes:ArrayBuffer)=>void;
  vi.spyOn(selected,"arrayBuffer").mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const get=vi.spyOn(api,"get");const controller=new AbortController();
  const attempt=identifyRetainedPdf(job,selected,controller.signal);const rejected=expect(attempt).rejects.toThrow(/verification/);
  await vi.waitFor(()=>expect(selected.arrayBuffer).toHaveBeenCalled());controller.abort();await rejected;
  finish(bytes.buffer);await Promise.resolve();expect(get).not.toHaveBeenCalled();
});
it("uses readonly status after an ambiguous POST without automatic replay",async()=>{
  const post=vi.spyOn(api,"post").mockRejectedValue(new Error("timeout"));const get=vi.spyOn(api,"get").mockResolvedValue({data:{events:[]}});
  await expect(repairRetainedPdf(job.job_id,{relative_path:"x",file_size:1,file_sha256:sha,source_export_fingerprint:"b".repeat(64)})).rejects.toThrow();
  await fetchRetainedPdfAudit(job.job_id);expect(post).toHaveBeenCalledTimes(1);expect(get).toHaveBeenCalledTimes(1);
});
