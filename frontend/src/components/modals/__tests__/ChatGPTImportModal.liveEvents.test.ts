import { afterEach, describe, expect, it, vi } from "vitest";

import { dispatchAccountImportRefresh } from "@/hooks/useLiveEvents";
import type { LiveEvent } from "@/lib/events/types";

function accountEvent(
  id: string,
  type: string,
  data: Record<string, unknown>
): LiveEvent {
  return {
    id,
    type,
    entity: "system",
    entity_id: String(data.job_id || "job-1"),
    thread_id: null,
    data,
    ts: Date.now(),
  };
}

describe("account import live refresh routing", () => {
  afterEach(() => vi.restoreAllMocks());

  it("routes committed conversation and media batches to existing refresh events", () => {
    const statuses = vi.fn();
    const threads = vi.fn();
    const gallery = vi.fn();
    window.addEventListener("cfy:account-import:status", statuses);
    window.addEventListener("cfy:threads:refresh", threads);
    window.addEventListener("cfy:gallery:refresh", gallery);

    dispatchAccountImportRefresh(
      accountEvent("event-conversations", "account_import.batch_committed", {
        job_id: "job-1",
        status: "running",
        batch_kind: "conversations",
      })
    );
    dispatchAccountImportRefresh(
      accountEvent("event-media", "account_import.batch_committed", {
        job_id: "job-1",
        status: "running",
        batch_kind: "media",
      })
    );

    expect(statuses).toHaveBeenCalledTimes(2);
    expect(threads).toHaveBeenCalledTimes(1);
    expect(gallery).toHaveBeenCalledTimes(1);
    window.removeEventListener("cfy:account-import:status", statuses);
    window.removeEventListener("cfy:threads:refresh", threads);
    window.removeEventListener("cfy:gallery:refresh", gallery);
  });

  it("refreshes both surfaces once on terminal completion", () => {
    const threads = vi.fn();
    const gallery = vi.fn();
    window.addEventListener("cfy:threads:refresh", threads);
    window.addEventListener("cfy:gallery:refresh", gallery);
    const event = accountEvent(
      "event-complete",
      "account_import.completed",
      { job_id: "job-2", status: "completed" }
    );

    dispatchAccountImportRefresh(event);
    dispatchAccountImportRefresh(event);

    expect(threads).toHaveBeenCalledTimes(1);
    expect(gallery).toHaveBeenCalledTimes(1);
    window.removeEventListener("cfy:threads:refresh", threads);
    window.removeEventListener("cfy:gallery:refresh", gallery);
  });
});
