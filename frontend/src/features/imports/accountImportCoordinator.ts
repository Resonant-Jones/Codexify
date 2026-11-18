import { getRuntimeConfigSync } from "@/lib/runtimeConfig";
import {
  commitOpenAIAccountImport,
  createOpenAIAccountImport,
  fetchOpenAIAccountImport,
  fetchOpenAIAccountImportManifest,
  normalizeImportRuntimeError,
  preflightBackendAvailability,
  uploadOpenAIAccountImportBatch,
  waitForAccountImportVerification,
  type AccountImportBrowserFile,
  type AccountImportJob,
  type AccountImportSourceSystem,
} from "@/lib/api";

export type AccountImportCoordinatorPhase =
  | "idle"
  | "preflighting"
  | "transferring"
  | "accepted"
  | "running"
  | "completed"
  | "completed_with_warnings"
  | "failed";

export type AccountImportCoordinatorSnapshot = {
  phase: AccountImportCoordinatorPhase;
  job: AccountImportJob | null;
  error: string | null;
  technicalDetail: string | null;
  verification?: { completed: number; total: number; bytes: number; totalBytes: number; stage: "reading" | "hashing" };
  selectedFileCount: number;
  selectedByteCount: number;
};

const STORAGE_KEY = "cfy.accountImport:v1";
const ARCHIVED_STORAGE_KEY = "cfy.accountImport:unavailable:v1";
const POLL_INTERVAL_MS = 1500;
const UPLOAD_BATCH_FILES = 25;
const UPLOAD_BATCH_TARGET_BYTES = 32 * 1024 * 1024;
// WebCrypto has no streaming digest interface. Bound its one-file allocation;
// larger staged files use 8 MiB slices with incremental SHA-256.
const MAX_BROWSER_RESUME_HASH_BYTES = 128 * 1024 * 1024;
const MAX_BROWSER_IMPORT_FILE_BYTES = 2 * 1024 * 1024 * 1024;
const LARGE_FILE_VERIFY_CHUNK_BYTES = 8 * 1024 * 1024;

const EMPTY_SNAPSHOT: AccountImportCoordinatorSnapshot = {
  phase: "idle",
  job: null,
  error: null,
  technicalDetail: null,
  selectedFileCount: 0,
  selectedByteCount: 0,
};

let snapshot = EMPTY_SNAPSHOT;
let pollTimer: ReturnType<typeof setTimeout> | null = null;
let refreshRun = 0;
let activeRun = 0;
let initialized = false;
let transferController: AbortController | null = null;
let accountStatusListener: EventListener | null = null;
// A client-local continuity check, never server import authority. It binds
// paths and content of even the files not yet admitted to the server.
let selectionFingerprint: string | null = null;
let selectionServer: string | null = null;

function currentImportServer(): string {
  const url = new URL(getRuntimeConfigSync().apiBaseUrl || "/", window.location.href);
  return url.origin + url.pathname.replace(/\/$/, "");
}

function archiveUnavailableJob(): boolean {
  // A 404 can mean a server/account switch, not loss of the original bytes.
  // Retain the exact checkpoint before releasing only the active UI reference.
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const prior = JSON.parse(window.localStorage.getItem(ARCHIVED_STORAGE_KEY) || "[]");
    if (!Array.isArray(prior)) return false;
    if (!prior.includes(raw)) prior.push(raw);
    window.localStorage.setItem(ARCHIVED_STORAGE_KEY, JSON.stringify(prior));
    return true;
  } catch { return false; }
}
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) listener();
}

function persist(next: AccountImportCoordinatorSnapshot): void {
  if (typeof window === "undefined") return;
  try {
    if (!next.job?.job_id) {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        v: 1,
        jobId: next.job.job_id,
        status: next.job.status,
        sourceSystem: next.job.source_system,
        selectionFingerprint: next.job.status === "receiving" ? selectionFingerprint : null,
        server: selectionServer,
        updatedAt: next.job.updated_at || null,
      })
    );
  } catch {
    // Storage can be unavailable in private mode; the in-memory coordinator remains valid.
  }
}

function setSnapshot(next: AccountImportCoordinatorSnapshot): void {
  snapshot = next;
  persist(next);
  notify();
}

function showLocalErrorWithoutPersisting(message: string): void {
  // Another tab may own a checkpoint that this tab has not observed. Never
  // overwrite shared storage merely because its Web Lock was unavailable.
  snapshot = { ...snapshot, phase: "failed", error: message, technicalDetail: null };
  notify();
}

export function hasArchivedAccountImport(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const entries = JSON.parse(window.localStorage.getItem(ARCHIVED_STORAGE_KEY) || "[]");
    return Array.isArray(entries) && entries.some((raw) => {
      const entry = JSON.parse(raw);
      return entry.v === 1 && typeof entry.jobId === "string" &&
        (entry.server === currentImportServer() || entry.server == null);
    });
  } catch { return false; }
}

export async function restoreArchivedAccountImport(): Promise<boolean> {
  ensureInitialized();
  if (transferController || snapshot.job) return false;
  const raw = window.localStorage.getItem(ARCHIVED_STORAGE_KEY);
  let entries: string[];
  try {
    const parsed = JSON.parse(raw || "[]");
    if (!Array.isArray(parsed)) return false;
    entries = parsed.filter((entry): entry is string => typeof entry === "string");
  } catch { return false; }
  // Read in reverse archival order, but only a server-authenticated owner
  // read can reactivate a browser checkpoint for the active account.
  for (let i = entries.length - 1; i >= 0; i -= 1) {
    let entry: { v?: number; jobId?: string; server?: string; sourceSystem?: string; selectionFingerprint?: string };
    try { entry = JSON.parse(entries[i]); } catch { continue; }
    if (entry.v !== 1 || !entry.jobId ||
        (entry.server && entry.server !== currentImportServer()) ||
        !/^[a-f0-9]{64}$/.test(entry.selectionFingerprint || "")) continue;
    let job: AccountImportJob;
    try { job = await fetchOpenAIAccountImport(entry.jobId); } catch { continue; }
    if (transferController || snapshot.job) return false;
    if (job.status !== "receiving" || job.job_id !== entry.jobId ||
        job.source_system !== entry.sourceSystem) continue;
    selectionFingerprint = entry.selectionFingerprint!;
    selectionServer = entry.server || currentImportServer();
    setSnapshot({ ...EMPTY_SNAPSHOT, phase: "failed", job,
      error: "Saved receiving job recovered. Select the original export to verify and resume.",
      technicalDetail: null });
    entries.splice(i, 1);
    window.localStorage.setItem(ARCHIVED_STORAGE_KEY, JSON.stringify(entries));
    return true;
  }
  return false;
}

function extractHttpStatus(error: unknown): number | null {
  const status = (error as { response?: { status?: unknown } } | null)?.response?.status;
  if (typeof status === "number") return status;
  return null;
}

function phaseForJob(job: AccountImportJob): AccountImportCoordinatorPhase {
  if (job.status === "queued") return "accepted";
  if (job.status === "running") return "running";
  if (job.status === "completed") return "completed";
  if (job.status === "completed_with_warnings") {
    return "completed_with_warnings";
  }
  if (job.status === "failed") return "failed";
  return "transferring";
}

function stopPolling(): void {
  if (pollTimer !== null) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
}

async function refreshJob(
  jobId: string,
  restoringReceiving = false
): Promise<void> {
  const run = ++refreshRun;
  stopPolling();
  try {
    if (selectionServer && selectionServer !== currentImportServer()) {
      setSnapshot({ ...snapshot, phase: "failed", error: "This saved import belongs to a different server. Return to its original server; the saved job and staged files are retained.", technicalDetail: null });
      return;
    }
    const job = await fetchOpenAIAccountImport(jobId);
    if (run !== refreshRun) return;
    if (job.status === "receiving") {
      setSnapshot({
        ...snapshot,
        phase: "failed",
        job,
        error: selectionFingerprint
          ? "The browser transfer ended before server queue acceptance. Select the same export folder again to verify and resume this job."
          : "This receiving import has no original complete-export fingerprint. Automatic resume is blocked because unstaged file identity cannot be established. Keep this job and its staged files for verified recovery.",
        technicalDetail: null,
      });
      return;
    }
    const phase = phaseForJob(job);
    setSnapshot({
      ...snapshot,
      phase,
      job,
      error:
        phase === "failed"
          ? String(job.error_details?.[0]?.message || "Account import failed.")
          : null,
      technicalDetail: null,
    });
    if (["accepted", "running"].includes(phase)) {
      pollTimer = setTimeout(() => void refreshJob(jobId), POLL_INTERVAL_MS);
    } else {
      stopPolling();
    }
  } catch (error) {
    if (run !== refreshRun) return;
    if (extractHttpStatus(error) === 404 && archiveUnavailableJob()) {
      selectionFingerprint = null;
      selectionServer = null;
      setSnapshot({
        ...snapshot,
        phase: "failed",
        job: null,
        error:
          "This saved account import job is no longer available for this account or server. Its checkpoint was retained separately and the stale browser reference was cleared. Confirm the selected account and server before starting another import.",
        technicalDetail: `HTTP 404 for job ${jobId}`,
      });
      return;
    }
    const normalized = normalizeImportRuntimeError(error, { phase: "upload" });
    setSnapshot({
      ...snapshot,
      error: normalized.message,
      technicalDetail: normalized.technicalDetail || null,
    });
    pollTimer = setTimeout(
      () => void refreshJob(jobId, restoringReceiving),
      POLL_INTERVAL_MS
    );
  }
}

function startPolling(jobId: string): void {
  stopPolling();
  pollTimer = setTimeout(() => void refreshJob(jobId), POLL_INTERVAL_MS);
}

function restorePersistedJob(): void {
  if (typeof window === "undefined") return;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as {
      v?: number;
      jobId?: string;
      status?: AccountImportJob["status"];
      sourceSystem?: unknown;
      selectionFingerprint?: unknown;
      server?: unknown;
    };
    if (parsed.v !== 1 || !parsed.jobId) return;
    selectionFingerprint = typeof parsed.selectionFingerprint === "string" &&
      /^[a-f0-9]{64}$/.test(parsed.selectionFingerprint)
      ? parsed.selectionFingerprint : null;
    selectionServer = typeof parsed.server === "string" ? parsed.server : null;
    // Fail-closed: only accept canonical source-system tokens. If the
    // persisted source is unknown, force the canonical server fetch to
    // re-establish the source-of-truth snapshot instead of carrying a
    // noncanonical value forward.
    if (
      parsed.sourceSystem !== undefined &&
      parsed.sourceSystem !== "openai" &&
      parsed.sourceSystem !== "anthropic"
    ) {
      snapshot = {
        ...EMPTY_SNAPSHOT,
        phase: "transferring",
        job: null,
      };
      void refreshJob(parsed.jobId, true);
      return;
    }
    snapshot = {
      ...EMPTY_SNAPSHOT,
      phase:
        parsed.status === "running"
          ? "running"
          : parsed.status === "completed"
            ? "completed"
            : parsed.status === "completed_with_warnings"
              ? "completed_with_warnings"
              : parsed.status === "failed"
                ? "failed"
                : parsed.status === "receiving"
                  ? "transferring"
                  : "accepted",
      job: {
        job_id: parsed.jobId,
        source_system: parsed.sourceSystem ?? "openai",
        status: parsed.status || "queued",
        total_file_count: 0,
        total_byte_count: 0,
        uploaded_file_count: 0,
        uploaded_byte_count: 0,
        imported_thread_count: 0,
        imported_message_count: 0,
        imported_media_count: 0,
        duplicate_count: 0,
        skipped_count: 0,
        warning_count: 0,
        failure_count: 0,
        warning_details: [],
        error_details: [],
      },
      error: null,
      technicalDetail: null,
      selectedFileCount: 0,
      selectedByteCount: 0,
    };
    if (parsed.status === "receiving") {
      void refreshJob(parsed.jobId, true);
    } else {
      void refreshJob(parsed.jobId);
    }
  } catch {
    // Ignore malformed or unavailable browser storage.
  }
}

function ensureInitialized(): void {
  if (initialized) return;
  initialized = true;
  restorePersistedJob();
  if (typeof window !== "undefined") {
    accountStatusListener = ((event: CustomEvent) => {
      const jobId = String(event.detail?.job_id || "");
      if (!transferController && jobId && jobId === snapshot.job?.job_id) {
        void refreshJob(jobId);
      }
    }) as EventListener;
    window.addEventListener("cfy:account-import:status", accountStatusListener);
  }
}

export function normalizeBrowserRelativePath(value: string): string {
  const raw = String(value || "")
    .replace(/\\/g, "/")
    .trim()
    .normalize("NFC");
  if (!raw || raw.startsWith("/") || /^[A-Za-z]:/.test(raw)) {
    throw new Error("Export files must use relative paths.");
  }
  const original = raw.split("/");
  if (original.includes("..")) {
    throw new Error("Export file paths cannot contain traversal segments.");
  }
  const parts = original.filter((part) => part && part !== ".");
  if (parts.length === 0) throw new Error("Export file path is empty.");
  const normalized = parts.join("/");
  const encoder = new TextEncoder();
  if (raw.includes("\0") || parts.some(part => encoder.encode(part).byteLength > 255) ||
      encoder.encode(normalized).byteLength > 1024) {
    throw new Error("Export file path exceeds the server's safe path limit. Rename the file before starting the import.");
  }
  return normalized;
}

function uploadBatches(
  files: AccountImportBrowserFile[]
): AccountImportBrowserFile[][] {
  const batches: AccountImportBrowserFile[][] = [];
  let batch: AccountImportBrowserFile[] = [];
  let batchBytes = 0;
  for (const item of files) {
    if (
      batch.length > 0 &&
      (batch.length >= UPLOAD_BATCH_FILES ||
        batchBytes + item.file.size > UPLOAD_BATCH_TARGET_BYTES)
    ) {
      batches.push(batch);
      batch = [];
      batchBytes = 0;
    }
    batch.push(item);
    batchBytes += item.file.size;
  }
  if (batch.length > 0) batches.push(batch);
  return batches;
}

function isTransientUploadError(error: unknown): boolean {
  const status = extractHttpStatus(error);
  const code = (error as { code?: string } | null)?.code;
  return [408, 502, 503, 504].includes(status ?? 0) ||
    ["ECONNABORTED", "ETIMEDOUT", "ERR_NETWORK"].includes(code ?? "");
}

function assertCurrentTransfer(run: number, signal: AbortSignal): void {
  if (run !== activeRun || signal.aborted) {
    throw new Error("Account import transfer was stopped.");
  }
}

// Native File reads and WebCrypto digests cannot be interrupted reliably. A
// timed-out step retains the Web Lock until the native operation settles, so
// retry cannot allocate a second large buffer while the first remains live.
export const ACCOUNT_IMPORT_VERIFY_STEP_TIMEOUT_MS = 30_000;
function blobBytes(blob: Blob): Promise<ArrayBuffer> {
  if (typeof blob.arrayBuffer === "function") return blob.arrayBuffer();
  // Older browser File implementations (and jsdom) expose FileReader instead.
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(new Error("Unable to read the selected export."));
    reader.readAsArrayBuffer(blob);
  });
}
async function boundedVerification<T>(operation: () => Promise<T>, signal: AbortSignal, stage: string): Promise<T> {
  if (signal.aborted) throw new Error("Account import transfer was stopped.");
  let rejectGate!: (error: Error) => void;
  let timer: ReturnType<typeof setTimeout> | null = null;
  const gate = new Promise<never>((_resolve, reject) => { rejectGate = reject; });
  const work = Promise.resolve().then(() => {
    if (signal.aborted) throw new Error("Account import transfer was stopped.");
    return operation();
  });
  const safeWork = work.catch(() => {
    throw new Error(`Local export verification failed while ${stage}. No remaining files were uploaded.`);
  });
  const aborted = () => {
    if (timer !== null) clearTimeout(timer);
    rejectGate(new Error("Account import transfer was stopped."));
  };
  signal.addEventListener("abort", aborted, { once: true });
  timer = setTimeout(() => {
    if (signal.aborted) return;
    const message = `Local export verification timed out while ${stage}. The current file operation must finish before retrying; no remaining files were uploaded.`;
    setSnapshot({ ...snapshot, phase: "failed", error: message, technicalDetail: null });
    rejectGate(new Error(message));
  }, ACCOUNT_IMPORT_VERIFY_STEP_TIMEOUT_MS);
  try {
    return await Promise.race([safeWork, gate]);
  } catch (error) {
    // The rejected deadline is not native cancellation. Keep the transfer and
    // cross-tab lock held until the underlying buffer/digest is no longer live.
    await work.catch(() => undefined);
    throw error;
  } finally {
    if (timer !== null) clearTimeout(timer);
    signal.removeEventListener("abort", aborted);
  }
}

async function hashLargeSelectedFile(
  file: File,
  run: number,
  signal: AbortSignal,
  onProgress: (bytes: number) => void
): Promise<string> {
  // Load the incremental implementation only for large files; WebCrypto has
  // no streaming SHA-256. Each native read is capped to one 8 MiB slice.
  const { sha256 } = await import("@noble/hashes/sha2.js");
  assertCurrentTransfer(run, signal);
  const hash = sha256.create();
  let readBytes = 0;
  while (readBytes < file.size) {
    assertCurrentTransfer(run, signal);
    const next = Math.min(readBytes + LARGE_FILE_VERIFY_CHUNK_BYTES, file.size);
    const slice = file.slice(readBytes, next);
    const bytes = await boundedVerification(() => blobBytes(slice), signal, "reading a selected file");
    if (bytes.byteLength !== next - readBytes) {
      throw new Error("The selected export conflicts with staged files. Nothing was uploaded.");
    }
    hash.update(new Uint8Array(bytes));
    readBytes = next;
    onProgress(readBytes);
  }
  return Array.from(hash.digest(), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function fingerprintSelection(
  files: AccountImportBrowserFile[],
  sourceSystem: AccountImportSourceSystem,
  run: number,
  signal: AbortSignal
): Promise<string> {
  // Only this digest is persisted in browser storage. Every original path,
  // byte count and content SHA-256 contributes, including files not uploaded.
  const { sha256 } = await import("@noble/hashes/sha2.js");
  const encoder = new TextEncoder();
  const aggregate = sha256.create().update(encoder.encode(`cfy-account-import-selection:v1\n${sourceSystem}\n`));
  const ordered = [...files].sort((a, b) => a.relativePath < b.relativePath ? -1 : a.relativePath > b.relativePath ? 1 : 0);
  const totalBytes = ordered.reduce((total, item) => total + item.file.size, 0);
  let doneBytes = 0;
  for (let i = 0; i < ordered.length; i += 1) {
    assertCurrentTransfer(run, signal);
    const item = ordered[i];
    const report = (bytes: number, stage: "reading" | "hashing") => {
      setSnapshot({ ...snapshot, verification: {
        completed: i, total: ordered.length, bytes: doneBytes + bytes, totalBytes, stage,
      } });
    };
    report(0, "reading");
    let digest: string;
    if (item.file.size > MAX_BROWSER_RESUME_HASH_BYTES) {
      digest = await hashLargeSelectedFile(item.file, run, signal, (bytes) => report(bytes, "hashing"));
    } else {
      const bytes = await boundedVerification(() => blobBytes(item.file), signal, "reading a selected file");
      if (bytes.byteLength !== item.file.size) throw new Error("Selected export contents changed during verification. Nothing was uploaded.");
      assertCurrentTransfer(run, signal);
      report(bytes.byteLength, "hashing");
      const hashed = await boundedVerification(() => crypto.subtle.digest("SHA-256", bytes), signal, "hashing a selected file");
      digest = Array.from(new Uint8Array(hashed), (byte) => byte.toString(16).padStart(2, "0")).join("");
    }
    assertCurrentTransfer(run, signal);
    aggregate.update(encoder.encode(JSON.stringify([item.relativePath, item.file.size, digest]) + "\n"));
    doneBytes += item.file.size;
    setSnapshot({ ...snapshot, verification: {
      completed: i + 1, total: ordered.length, bytes: doneBytes, totalBytes, stage: "hashing",
    } });
  }
  return Array.from(aggregate.digest(), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function remainingFiles(
  job: AccountImportJob,
  files: AccountImportBrowserFile[],
  run: number,
  signal: AbortSignal
): Promise<AccountImportBrowserFile[]> {
  const manifest = await fetchOpenAIAccountImportManifest(job.job_id);
  assertCurrentTransfer(run, signal);
  if (manifest.job_id !== job.job_id || manifest.source_system !== job.source_system ||
      manifest.status !== "receiving" || manifest.total_file_count !== files.length ||
      manifest.total_byte_count !== files.reduce((sum, item) => sum + item.file.size, 0)) {
    throw new Error("The selected export does not match this receiving job. Nothing was uploaded.");
  }
  const selected = new Map(files.map((item) => [item.relativePath, item]));
  if (selected.size !== files.length) throw new Error("Export contains duplicate normalized paths.");
  if (manifest.files.some((entry) => entry.size > MAX_BROWSER_RESUME_HASH_BYTES &&
      typeof selected.get(entry.path)?.file.slice !== "function")) {
    throw new Error("A staged file exceeds this browser's safe verification limit because bounded file slices are unavailable. Keep this job and use a modern browser.");
  }
  const staged = new Set<string>();
  // Verify every durable checkpoint entry before sending any remaining bytes.
  // Hash one file at a time; do not hold a multi-gigabyte export in memory.
  const totalBytes = manifest.files.reduce((sum, entry) => sum + entry.size, 0);
  let verifiedBytes = 0;
  for (const entry of manifest.files) {
    const item = selected.get(entry.path);
    if (!item || staged.has(entry.path) || item.file.size !== entry.size ||
        !/^[a-f0-9]{64}$/.test(entry.sha256)) {
      throw new Error("The selected export conflicts with staged files. Nothing was uploaded.");
    }
    assertCurrentTransfer(run, signal);
    const progress = { completed: staged.size, total: manifest.files.length, bytes: verifiedBytes, totalBytes };
    setSnapshot({ ...snapshot, verification: { ...progress, stage: "reading" } });
    let hex: string;
    if (entry.size > MAX_BROWSER_RESUME_HASH_BYTES) {
      hex = await hashLargeSelectedFile(item.file, run, signal, (bytes) => {
        setSnapshot({ ...snapshot, verification: { ...progress, bytes: verifiedBytes + bytes, stage: "hashing" } });
      });
    } else {
      const bytes = await boundedVerification(() => item.file.arrayBuffer(), signal, "reading a selected file");
      assertCurrentTransfer(run, signal);
      setSnapshot({ ...snapshot, verification: { ...progress, stage: "hashing" } });
      const digest = await boundedVerification(() => crypto.subtle.digest("SHA-256", bytes), signal, "hashing a selected file");
      hex = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    }
    assertCurrentTransfer(run, signal);
    if (hex !== entry.sha256) {
      throw new Error("The selected export conflicts with staged files. Nothing was uploaded.");
    }
    staged.add(entry.path);
    verifiedBytes += entry.size;
    setSnapshot({ ...snapshot, verification: { completed: staged.size, total: manifest.files.length, bytes: verifiedBytes, totalBytes, stage: "hashing" } });
  }
  return files.filter((item) => !staged.has(item.relativePath));
}

async function transferBatch(
  job: AccountImportJob,
  batch: AccountImportBrowserFile[],
  run: number,
  signal: AbortSignal
): Promise<AccountImportJob> {
  // Only file staging is replayed. Path+hash+size are checked under the server
  // row lock, so a lost success response cannot create a second file.
  for (let attempt = 0; ; attempt += 1) {
    assertCurrentTransfer(run, signal);
    try {
      return await uploadOpenAIAccountImportBatch(job.job_id, batch, signal);
    } catch (error) {
      assertCurrentTransfer(run, signal);
      if (!isTransientUploadError(error) || attempt >= 2) throw error;
      const current = await fetchOpenAIAccountImport(job.job_id);
      assertCurrentTransfer(run, signal);
      if (current.status !== "receiving") return current;
      await new Promise((resolve) => setTimeout(resolve, 1000 * (attempt + 1)));
    }
  }
}

export async function startOpenAIAccountImport(
  selectedFiles: AccountImportBrowserFile[],
  sourceSystem: AccountImportSourceSystem = "openai"
): Promise<AccountImportJob> {
  ensureInitialized();
  // A status event or unmount must not allow a second upload loop in this tab.
  if (transferController) throw new Error("An account export transfer is already active.");
  const normalizedFiles = selectedFiles.map((item) => ({
    file: item.file,
    relativePath: normalizeBrowserRelativePath(item.relativePath),
  }));
  if (!normalizedFiles.length) throw new Error("No export files were selected.");
  if (new Set(normalizedFiles.map((item) => item.relativePath)).size !== normalizedFiles.length) {
    throw new Error("Export contains duplicate normalized paths.");
  }
  if (normalizedFiles.some((item) => item.file.size > MAX_BROWSER_IMPORT_FILE_BYTES)) {
    throw new Error("Browser account import does not support files larger than the backend 2 GiB limit. No job was created or changed.");
  }
  if (normalizedFiles.some((item) => item.file.size > MAX_BROWSER_RESUME_HASH_BYTES && typeof item.file.slice !== "function")) {
    throw new Error("Large browser imports require bounded file slices for safe resume. No job was created or changed; use a modern browser.");
  }
  if (["preflighting", "transferring", "accepted", "running"].includes(snapshot.phase)) {
    if (snapshot.job && snapshot.job.source_system !== sourceSystem) {
      throw new Error(`An account export import is already active for ${snapshot.job.source_system}; finish or cancel it before starting a ${sourceSystem} import.`);
    }
    throw new Error("An account export import is already active.");
  }
  const resume = snapshot.job?.status === "receiving" ? snapshot.job : null;
  if (resume && resume.source_system !== sourceSystem) {
    throw new Error("Resume requires the original account source.");
  }
  if (resume && selectionServer && selectionServer !== currentImportServer()) {
    throw new Error("This saved import belongs to a different server. Return to its original server; the saved job and staged files are retained.");
  }
  // Web Locks survive component lifetimes and exclude concurrent updated tabs.
  // No unsafe localStorage lease or silent takeover when the owner is unknown.
  if (!navigator.locks) {
    const message = "Safe account import requires a browser with Web Locks support.";
    showLocalErrorWithoutPersisting(message);
    throw new Error(message);
  }
  return navigator.locks.request("cfy.account-import-transfer", { ifAvailable: true }, async (lock) => {
    if (!lock || transferController) {
      const message = "An account export transfer is already active in another tab.";
      if (!transferController) showLocalErrorWithoutPersisting(message);
      throw new Error(message);
    }
    const controller = new AbortController();
    transferController = controller;
    const run = ++activeRun;
    refreshRun += 1;
    stopPolling();
    const selectedByteCount = normalizedFiles.reduce((sum, item) => sum + item.file.size, 0);
    setSnapshot({
      phase: "preflighting", job: resume, error: null, technicalDetail: null,
      selectedFileCount: normalizedFiles.length, selectedByteCount,
    });
    try {
      const availability = await preflightBackendAvailability();
      assertCurrentTransfer(run, controller.signal);
      if (!availability.ok) throw Object.assign(new Error(availability.message), { technicalDetail: availability.technicalDetail });
      let job: AccountImportJob;
      if (resume) {
        job = await fetchOpenAIAccountImport(resume.job_id);
      } else {
        const fingerprint = await fingerprintSelection(normalizedFiles, sourceSystem, run, controller.signal);
        assertCurrentTransfer(run, controller.signal);
        job = await createOpenAIAccountImport({
          total_file_count: normalizedFiles.length,
          total_byte_count: selectedByteCount,
          source_system: sourceSystem,
        });
        // Bind the selection to this new job before the first upload.
        selectionFingerprint = fingerprint;
        selectionServer = currentImportServer();
      }
      assertCurrentTransfer(run, controller.signal);
      if (job.source_system !== sourceSystem) throw new Error("The account import source changed.");
      if (job.status === "receiving") {
        if (resume) {
          if (!selectionFingerprint) {
            throw new Error("This saved job lacks complete-export verification. Keep this job and its staged bytes for verified recovery; automatic resume cannot establish original unstaged file identity.");
          }
          const fingerprint = await fingerprintSelection(normalizedFiles, sourceSystem, run, controller.signal);
          assertCurrentTransfer(run, controller.signal);
          if (fingerprint !== selectionFingerprint) {
            throw new Error("The selected export content or file paths differ from the original selection. Nothing was uploaded.");
          }
        }
        const pending = resume
          ? await remainingFiles(job, normalizedFiles, run, controller.signal)
          : normalizedFiles;
        setSnapshot({ ...snapshot, phase: "transferring", job, verification: undefined });
        for (const batch of uploadBatches(pending)) {
          job = await transferBatch(job, batch, run, controller.signal);
          assertCurrentTransfer(run, controller.signal);
          setSnapshot({ ...snapshot, phase: phaseForJob(job), job });
          if (job.status !== "receiving") break;
        }
        if (job.status === "receiving") {
          try {
            job = await commitOpenAIAccountImport(job.job_id);
          } catch (error) {
            // A lost commit response is not authority to enqueue another worker.
            const current = await fetchOpenAIAccountImport(job.job_id);
            if (current.status === "receiving") throw error;
            job = current;
          }
        }
      }
      assertCurrentTransfer(run, controller.signal);
      setSnapshot({ ...snapshot, phase: phaseForJob(job), job });
      if (["queued", "running"].includes(job.status)) startPolling(job.job_id);
      return job;
    } catch (error: unknown) {
      if (run === activeRun) {
        const normalized = normalizeImportRuntimeError(error, { phase: "upload" });
        const staleResume = Boolean(resume && extractHttpStatus(error) === 404 && archiveUnavailableJob());
        if (staleResume) { selectionFingerprint = null; selectionServer = null; }
        setSnapshot({ ...snapshot, phase: "failed", job: staleResume ? null : snapshot.job,
          error: snapshot.job?.status === "receiving"
            ? staleResume
              ? "This saved import job is unavailable on the selected server. Its checkpoint was retained separately and its stale browser reference was cleared. Confirm the selected account and server before starting another import."
              : selectionFingerprint
                ? `${normalized.message} Staged files are retained. Select the same export folder to verify and resume.`
                : normalized.message
            : normalized.message,
          technicalDetail: normalized.technicalDetail || null });
      }
      throw error;
    } finally {
      // A prompt timeout is not cancellation of native buffers. Retain the
      // same-tab owner and Web Lock while the API quarantines late work.
      await waitForAccountImportVerification();
      if (transferController === controller) transferController = null;
    }
  });
}

export function subscribeAccountImportCoordinator(listener: () => void): () => void {
  ensureInitialized();
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getAccountImportCoordinatorSnapshot(): AccountImportCoordinatorSnapshot {
  ensureInitialized();
  return snapshot;
}

export function clearAccountImportCoordinatorResult(): void {
  transferController?.abort();
  stopPolling();
  refreshRun += 1;
  activeRun += 1;
  selectionFingerprint = null;
  selectionServer = null;
  setSnapshot(EMPTY_SNAPSHOT);
}

export function resetAccountImportCoordinatorForTests(): void {
  transferController?.abort();
  stopPolling();
  refreshRun += 1;
  activeRun += 1;
  selectionFingerprint = null;
  selectionServer = null;
  initialized = false;
  snapshot = EMPTY_SNAPSHOT;
  listeners.clear();
  if (typeof window !== "undefined") {
    if (accountStatusListener) {
      window.removeEventListener(
        "cfy:account-import:status",
        accountStatusListener
      );
      accountStatusListener = null;
    }
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Test/browser storage can be unavailable.
    }
  }
}
