import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PersonalSetupCard from "../PersonalSetupCard";
import { BootstrapHumanAction, BootstrapWorkflow, type BootstrapReadiness } from "@/contracts/bootstrapReadiness.generated";
import { isTauriRuntime } from "@/lib/runtimeConfig";
import { runSetupCli } from "@/lib/runtimeBootstrap";
vi.mock("@/lib/runtimeConfig", () => ({ isTauriRuntime: vi.fn(() => false) }));
vi.mock("@/lib/runtimeBootstrap", () => ({ runSetupCli: vi.fn() }));
const readiness: BootstrapReadiness = { version: 1, workflow: BootstrapWorkflow.COMPLETE, coreReady: true, inferenceReady: false, humanAction: BootstrapHumanAction.PROVIDER_MODEL_CHOICE_REQUIRED };
const renderCard = (overrides = {}) => render(<PersonalSetupCard readiness={{ ...readiness, ...overrides }} onOpenSettings={vi.fn()} />);
describe("personal setup", () => {
  beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); vi.mocked(isTauriRuntime).mockReturnValue(false); });
  afterEach(cleanup);
  it("keeps missing inference visible and persists dismissal with deliberate resume", () => {
    const first = renderCard();
    expect(screen.getByText(/Chat is unavailable until/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Later" }));
    first.unmount(); renderCard();
    expect(screen.queryByRole("region", { name: "Personal setup" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Resume personal setup/ }));
    expect(screen.getByRole("region", { name: "Personal setup" })).toBeInTheDocument();
  });
  it("pauses at provider choice without invoking host operations from web", async () => {
    renderCard(); fireEvent.click(screen.getByRole("button", { name: "Finish personal setup" }));
    await screen.findByText(/Choose your provider and model/);
    expect(runSetupCli).not.toHaveBeenCalled();
  });
  it("uses only the existing native helper after deliberate consent, then pauses", async () => {
    vi.mocked(isTauriRuntime).mockReturnValue(true);
    vi.mocked(runSetupCli).mockResolvedValue({ ok: true, step: "setup" });
    renderCard(); expect(runSetupCli).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Finish personal setup" }));
    await waitFor(() => expect(runSetupCli).toHaveBeenCalledTimes(1));
    await screen.findByText(/Choose your provider and model/);
    expect(screen.getByRole("region", { name: "Personal setup" })).toHaveAttribute("data-human-action", BootstrapHumanAction.PROVIDER_MODEL_CHOICE_REQUIRED);
  });
  it("observes human action when core becomes ready after initial render", () => {
    const view = renderCard({ coreReady: false, humanAction: BootstrapHumanAction.NONE });
    view.rerender(<PersonalSetupCard readiness={readiness} onOpenSettings={vi.fn()} />);
    expect(screen.getByRole("region", { name: "Personal setup" })).toHaveAttribute("data-human-action", BootstrapHumanAction.PROVIDER_MODEL_CHOICE_REQUIRED);
  });
  it("does not label a core outage as incomplete personal setup", () => {
    renderCard({ coreReady: false }); expect(screen.queryByRole("region", { name: "Personal setup" })).not.toBeInTheDocument();
  });
  it("removes the card only after inference is observed ready", () => {
    renderCard({ inferenceReady: true }); expect(screen.queryByRole("region", { name: "Personal setup" })).not.toBeInTheDocument();
  });
});
