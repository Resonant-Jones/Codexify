import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GuardianEventSource } from "@/lib/guardianEventSource";

async function flushAsync(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

describe("GuardianEventSource backoff behavior", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(console, "info").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("retries with increasing backoff steps", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 503,
      body: null,
    }));
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(Math, "random").mockReturnValue(0.5); // deterministic jitter

    const source = new GuardianEventSource("http://localhost/api/events");
    await flushAsync();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const infoSpy = vi.mocked(console.info);
    expect(
      infoSpy.mock.calls.some((call) => String(call[0]).includes("250ms"))
    ).toBe(true);

    vi.advanceTimersByTime(250);
    await flushAsync();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(
      infoSpy.mock.calls.some((call) => String(call[0]).includes("500ms"))
    ).toBe(true);

    vi.advanceTimersByTime(500);
    await flushAsync();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(
      infoSpy.mock.calls.some((call) => String(call[0]).includes("1000ms"))
    ).toBe(true);

    source.close();
  });

  it("stops reconnecting after a 401 unauthorized response", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 401,
      body: null,
    }));
    vi.stubGlobal("fetch", fetchMock);
    const unauthorizedSpy = vi.fn();

    const source = new GuardianEventSource("http://localhost/api/events", {
      onUnauthorized: unauthorizedSpy,
    });

    await flushAsync();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(unauthorizedSpy).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(10000);
    await flushAsync();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(source.readyState).toBe(GuardianEventSource.CLOSED);
  });
});
