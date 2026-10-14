import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WebRuntimeStartupGate from "@/components/bootstrap/WebRuntimeStartupGate";

const preflightMock = vi.fn();

vi.mock("@/lib/api", () => ({
  getBackendOutageRemainingMs: vi.fn(() => 0),
  preflightBackendAvailability: (...args: unknown[]) => preflightMock(...args),
}));

const NOTICE_TITLE = "Backend connection delayed";
const FAILURE_DETAIL = "connect ECONNREFUSED 127.0.0.1:8888";

function queryNoticeTitle() {
  return screen.queryByText(NOTICE_TITLE);
}

function getOkButton() {
  return screen.getByRole("button", {
    name: /dismiss the backend connection notice/i,
  });
}

async function settle() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
}

async function advanceTimers(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("WebRuntimeStartupGate", () => {
  beforeEach(() => {
    preflightMock.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("renders children immediately when disabled", () => {
    render(
      <WebRuntimeStartupGate enabled={false}>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );

    expect(screen.getByText("App shell")).toBeInTheDocument();
    expect(queryNoticeTitle()).toBeNull();
    expect(screen.queryByText("OK")).toBeNull();
    expect(preflightMock).not.toHaveBeenCalled();
  });

  it("shows a non-blocking degraded-state notice after a failed preflight", async () => {
    vi.useFakeTimers();
    preflightMock.mockResolvedValue({
      ok: false,
      technicalDetail: FAILURE_DETAIL,
    });
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );
    await settle();

    const gateTitle = screen.getByText(NOTICE_TITLE);
    const gateOverlay = gateTitle.closest(".fixed");

    expect(gateTitle).toBeInTheDocument();
    expect(screen.getByText("App shell")).toBeInTheDocument();
    expect(gateOverlay).toHaveClass("z-[1300]");
    expect(gateOverlay).toHaveClass("pointer-events-none");
    // A failed preflight surfaces exactly one notice carrying both actions.
    expect(screen.getAllByText(NOTICE_TITLE)).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Retry now" })).toBeInTheDocument();
    expect(getOkButton()).toBeInTheDocument();
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  it("does not present a failure notice before the first preflight result", async () => {
    vi.useFakeTimers();
    let resolvePreflight!: (value: { ok: boolean; technicalDetail: string }) => void;
    preflightMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePreflight = resolve;
        })
    );
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );
    await settle();

    // The probe is still in flight, so nothing is confirmed yet.
    expect(preflightMock).toHaveBeenCalledTimes(1);
    expect(queryNoticeTitle()).toBeNull();
    expect(screen.getByText("App shell")).toBeInTheDocument();

    await act(async () => {
      resolvePreflight({ ok: false, technicalDetail: FAILURE_DETAIL });
    });

    expect(screen.getByText(NOTICE_TITLE)).toBeInTheDocument();
  });

  it("dismisses the notice immediately when OK is pressed", async () => {
    vi.useFakeTimers();
    preflightMock.mockResolvedValue({
      ok: false,
      technicalDetail: FAILURE_DETAIL,
    });
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );
    await settle();
    expect(screen.getByText(NOTICE_TITLE)).toBeInTheDocument();

    fireEvent.click(getOkButton());

    expect(queryNoticeTitle()).toBeNull();
    expect(screen.queryByText(FAILURE_DETAIL)).toBeNull();
    // Acknowledgement is display-only: the shell stays mounted and usable.
    expect(screen.getByText("App shell")).toBeInTheDocument();
  });

  it("continues automatic retries after the notice is dismissed", async () => {
    vi.useFakeTimers();
    preflightMock.mockResolvedValue({
      ok: false,
      technicalDetail: FAILURE_DETAIL,
    });
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );
    await settle();
    fireEvent.click(getOkButton());

    const callsAtDismissal = preflightMock.mock.calls.length;
    await advanceTimers(20_000);

    // Backoff keeps probing well past the dismissal point.
    expect(preflightMock.mock.calls.length).toBeGreaterThan(callsAtDismissal);
  });

  it("does not reopen a dismissed notice while the failure episode continues", async () => {
    vi.useFakeTimers();
    preflightMock.mockResolvedValue({
      ok: false,
      technicalDetail: FAILURE_DETAIL,
    });
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );
    await settle();
    fireEvent.click(getOkButton());
    expect(queryNoticeTitle()).toBeNull();

    await advanceTimers(30_000);

    // Polling and retries rerender the gate repeatedly; the acknowledged
    // notice must stay gone for the rest of the episode.
    expect(preflightMock.mock.calls.length).toBeGreaterThan(2);
    expect(queryNoticeTitle()).toBeNull();
    expect(screen.getByText("App shell")).toBeInTheDocument();
  });

  it("keeps Retry now working as an immediate check", async () => {
    vi.useFakeTimers();
    preflightMock.mockResolvedValue({
      ok: false,
      technicalDetail: FAILURE_DETAIL,
    });
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );
    await settle();

    const callsBeforeRetry = preflightMock.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Retry now" }));
    await settle();

    expect(preflightMock.mock.calls.length).toBeGreaterThan(callsBeforeRetry);
    expect(screen.getByText(NOTICE_TITLE)).toBeInTheDocument();
    expect(getOkButton()).toBeInTheDocument();
  });

  it("hides the degraded notice once the backend probe succeeds", async () => {
    preflightMock.mockResolvedValue({ ok: true });
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );

    await screen.findByText("App shell");
    // The notice is only shown when ready=false; once preflight returns ok,
    // the gate clears and the notice is removed from the DOM.
    expect(queryNoticeTitle()).toBeNull();
    expect(preflightMock).toHaveBeenCalled();
  });

  it("clears a dismissed notice on successful recovery", async () => {
    vi.useFakeTimers();
    preflightMock.mockResolvedValueOnce({
      ok: false,
      technicalDetail: FAILURE_DETAIL,
    });
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );
    await settle();
    fireEvent.click(getOkButton());
    expect(queryNoticeTitle()).toBeNull();

    // Recovery is never blocked by the acknowledgement.
    preflightMock.mockResolvedValue({ ok: true });
    await advanceTimers(5_000);

    expect(queryNoticeTitle()).toBeNull();
    expect(screen.getByText("App shell")).toBeInTheDocument();
  });

  it("raises a fresh notice on a newly mounted gate instance after a dismissal", async () => {
    vi.useFakeTimers();
    preflightMock.mockResolvedValue({
      ok: false,
      technicalDetail: FAILURE_DETAIL,
    });

    const first = render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );
    await settle();
    fireEvent.click(getOkButton());
    expect(queryNoticeTitle()).toBeNull();

    first.unmount();

    // Dismissal is per-mount: a fresh gate instance may notify again.
    render(
      <WebRuntimeStartupGate enabled>
        <div>App shell</div>
      </WebRuntimeStartupGate>
    );
    await settle();

    expect(screen.getByText(NOTICE_TITLE)).toBeInTheDocument();
    expect(getOkButton()).toBeInTheDocument();
  });
});