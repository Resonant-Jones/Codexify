import {
  commitOpenAIAccountImport,
  createOpenAIAccountImport,
  fetchOpenAIAccountImport,
  normalizeImportRuntimeError,
  preflightBackendAvailability,
  uploadOpenAIAccountImportBatch,
  type AccountImportBrowserFile,
  type AccountImportJob,
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
  selectedFileCount: number;
  selectedByteCount: number;
};

const STORAGE_KEY = "cfy.accountImport:v1";
const POLL_INTERVAL_MS = 1500;
const UPLOAD_BATCH_FILES = 25;
const UPLOAD_BATCH_TARGET_BYTES = 32 * 1024 * 1024;

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
let pollingUserId: string | undefined;
let accountStatusListener: EventListener | null = null;
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
    const job = await fetchOpenAIAccountImport(jobId, pollingUserId);
    if (run !== refreshRun) return;
    if (restoringReceiving && job.status === "receiving") {
      setSnapshot({
        ...snapshot,
        phase: "failed",
        job,
        error:
          "The browser transfer ended before server queue acceptance. Select the export again to retry.",
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
    if (extractHttpStatus(error) === 404) {
      setSnapshot({
        ...snapshot,
        phase: "failed",
        job: null,
        error:
          "This saved account import job is no longer available for this account or server. The stale browser reference was cleared. Start the import again if needed.",
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

function startPolling(jobId: string, userId?: string): void {
  stopPolling();
  pollingUserId = userId;
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
    };
    if (parsed.v !== 1 || !parsed.jobId) return;
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
        source_system: "openai",
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
      if (jobId && jobId === snapshot.job?.job_id) {
        void refreshJob(jobId);
      }
    }) as EventListener;
    window.addEventListener("cfy:account-import:status", accountStatusListener);
  }
}

export function normalizeBrowserRelativePath(value: string): string {
  const raw = String(value || "")
    .replaceAll("\\", "/")
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
  return parts.join("/");
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

export async function startOpenAIAccountImport(
  selectedFiles: AccountImportBrowserFile[],
  userId?: string
): Promise<AccountImportJob> {
  ensureInitialized();
  const normalizedFiles = selectedFiles.map((item) => ({
    file: item.file,
    relativePath: normalizeBrowserRelativePath(item.relativePath),
  }));
  if (normalizedFiles.length === 0) {
    throw new Error("No export files were selected.");
  }
  if (
    ["preflighting", "transferring", "accepted", "running"].includes(
      snapshot.phase
    )
  ) {
    throw new Error("An account export import is already active.");
  }

  const run = ++activeRun;
  pollingUserId = userId;
  const selectedByteCount = normalizedFiles.reduce(
    (total, item) => total + item.file.size,
    0
  );
  setSnapshot({
    phase: "preflighting",
    job: null,
    error: null,
    technicalDetail: null,
    selectedFileCount: normalizedFiles.length,
    selectedByteCount,
  });

  try {
    const availability = await preflightBackendAvailability();
    if (!availability.ok) {
      throw Object.assign(new Error(availability.message), {
        technicalDetail: availability.technicalDetail,
      });
    }
    let job = await createOpenAIAccountImport(
      {
        total_file_count: normalizedFiles.length,
        total_byte_count: selectedByteCount,
      },
      userId
    );
    if (run !== activeRun) return job;
    setSnapshot({ ...snapshot, phase: "transferring", job });
    for (const batch of uploadBatches(normalizedFiles)) {
      job = await uploadOpenAIAccountImportBatch(job.job_id, batch, userId);
      if (run !== activeRun) return job;
      setSnapshot({ ...snapshot, phase: "transferring", job });
    }
    job = await commitOpenAIAccountImport(job.job_id, userId);
    if (run !== activeRun) return job;
    setSnapshot({ ...snapshot, phase: phaseForJob(job), job });
    if (["queued", "running"].includes(job.status)) {
      startPolling(job.job_id, userId);
    }
    return job;
  } catch (error: unknown) {
    const normalized = normalizeImportRuntimeError(error, { phase: "upload" });
    const errorRecord =
      error instanceof Error
        ? (error as Error & { technicalDetail?: string })
        : null;
    setSnapshot({
      ...snapshot,
      phase: "failed",
      error: normalized.message || errorRecord?.message || String(error),
      technicalDetail:
        normalized.technicalDetail || errorRecord?.technicalDetail || null,
    });
    throw error;
  }
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
  stopPolling();
  refreshRun += 1;
  activeRun += 1;
  pollingUserId = undefined;
  setSnapshot(EMPTY_SNAPSHOT);
}

export function resetAccountImportCoordinatorForTests(): void {
  stopPolling();
  refreshRun += 1;
  activeRun += 1;
  pollingUserId = undefined;
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
