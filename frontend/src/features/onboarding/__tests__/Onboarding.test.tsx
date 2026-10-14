import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import OnboardingProvider from "../OnboardingProvider";
import HelpAndLearning from "../HelpAndLearning";
import PeopleSetupBanner from "../PeopleSetupBanner";
import { DEFAULT_STATE, type OnboardingState } from "../onboardingTypes";
const mocks = vi.hoisted(() => ({
  fetch: vi.fn(),
  patch: vi.fn(),
  social: vi.fn(),
  claim: vi.fn(),
  capability: "unavailable",
}));
vi.mock("../onboardingApi", () => ({ fetchOnboarding: mocks.fetch, patchOnboarding: mocks.patch }));
vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapability: () => ({ state: mocks.capability }),
}));
vi.mock("@/lib/direct-messages", () => ({
  fetchOwnSocialIdentity: mocks.social,
  claimSocialIdentityUsername: mocks.claim,
}));
let durable: OnboardingState;
const unsetProfile = {
  node_id: "node",
  profile_id: "profile",
  username: null,
  username_state: "unset",
  display_name: null,
  avatar_url: null,
};
function mount(ready = true, mobile = false) {
  return render(
    <OnboardingProvider ready={ready} mobile={mobile}>
      <div>Usable workspace</div>
      <HelpAndLearning />
      <PeopleSetupBanner />
    </OnboardingProvider>
  );
}
const dialog = () => screen.getByRole("dialog", { name: "Codexify onboarding" });
async function next() {
  fireEvent.click(
    within(dialog()).getByRole("button", { name: /^(Continue|Skip username|Finish)$/ })
  );
  await waitFor(() => expect(mocks.patch).toHaveBeenCalled());
}
afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  durable = { ...DEFAULT_STATE };
  mocks.capability = "unavailable";
  mocks.fetch.mockImplementation(async () => ({ ...durable }));
  mocks.patch.mockImplementation(async (changes) => {
    durable = { ...durable, ...changes };
    return { ...durable };
  });
  mocks.social.mockResolvedValue(unsetProfile);
  mocks.claim.mockResolvedValue({ ...unsetProfile, username: "alias", username_state: "active" });
});
describe("account introduction", () => {
  it("waits for shell readiness and leaves the workspace mounted", async () => {
    const view = mount(false);
    expect(mocks.fetch).not.toHaveBeenCalled();
    expect(screen.getByText("Usable workspace")).toBeVisible();
    view.rerender(
      <OnboardingProvider ready mobile={false}>
        <div>Usable workspace</div>
      </OnboardingProvider>
    );
    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("Usable workspace")).toBeVisible();
  });
  it("persists skip and does not reopen next mount", async () => {
    const view = mount();
    await screen.findByRole("dialog");
    fireEvent.click(within(dialog()).getByText("Skip for now"));
    await waitFor(() => expect(durable.status).toBe("skipped"));
    view.unmount();
    mount();
    await screen.findByText("Finish setting up Codexify");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
  it("resumes the saved semantic step", async () => {
    durable.status = "skipped";
    durable.last_step_key = "identity";
    mount();
    fireEvent.click((await screen.findAllByRole("button", { name: "Resume setup" }))[0]);
    expect(within(dialog()).getByText("Your identity, your choice")).toBeVisible();
  });
  it.each([false, true])(
    "finishes the appropriate presentation with optional username (%s)",
    async (mobile) => {
      mount(true, mobile);
      await screen.findByRole("dialog");
      for (const heading of [
        "Your identity, your choice",
        "Choose a username",
        mobile ? "Phone navigation" : "Desktop navigation",
        "One workspace, several surfaces",
        "Keep learning at your pace",
      ]) {
        fireEvent.click(
          within(dialog()).getByRole("button", { name: /^(Continue|Skip username)$/ })
        );
        await waitFor(() =>
          expect(within(dialog()).getByRole("heading", { name: heading })).toBeVisible()
        );
      }
      fireEvent.click(within(dialog()).getByText("Finish"));
      await waitFor(() => expect(durable.status).toBe("completed"));
      expect(mobile ? durable.mobile_tour_completed : durable.desktop_tour_completed).toBe(true);
      expect(mocks.social).not.toHaveBeenCalled();
      expect(mocks.claim).not.toHaveBeenCalled();
    }
  );
  it.each([false, true])("teaches correct navigation language (%s)", async (mobile) => {
    durable.status = "skipped";
    durable.last_step_key = "navigation";
    mount(true, mobile);
    fireEvent.click((await screen.findAllByText("Resume setup"))[0]);
    expect(
      within(dialog()).getByText(
        mobile
          ? /Access your workspace.*mobile drawer/
          : /Threads and Projects live in the workspace\/sidebar/
      )
    ).toBeVisible();
    if (mobile) expect(within(dialog()).queryByText(/left sidebar/i)).toBeNull();
  });
  it("keeps username setup separate and removes the prompt after claim", async () => {
    durable.status = "completed";
    mocks.capability = "available";
    mount();
    fireEvent.click(await screen.findByText("Choose username"));
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "ALIAS" } });
    fireEvent.click(within(dialog()).getByText("Claim username"));
    await screen.findByText("Your username is @alias.");
    expect(mocks.claim).toHaveBeenCalledWith("alias");
    expect(screen.queryByText("Set up messaging")).toBeNull();
    expect(durable.status).toBe("completed");
  });
  it("never asks for a username or calls messaging when unavailable", async () => {
    durable.status = "completed";
    mount();
    await waitFor(() => expect(mocks.fetch).toHaveBeenCalled());
    expect(screen.queryByText("Set up messaging")).toBeNull();
    expect(mocks.social).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Restart onboarding"));
    await next();
    await next();
    expect(screen.queryByLabelText("Username")).toBeNull();
    expect(screen.getByText(/People messaging is not enabled/)).toBeVisible();
  });
  it("opens passive Tips later and hides unavailable capability entries", async () => {
    durable.status = "completed";
    mount();
    fireEvent.click(screen.getByText("Open Codexify Tips"));
    const tips = await screen.findByRole("dialog", { name: "Codexify Tips" });
    expect(within(tips).getByText("Talk with Guardian")).toBeVisible();
    expect(within(tips).queryByText("Choose a username")).toBeNull();
  });
  it("restarts the device tour without resetting global completion", async () => {
    durable.status = "completed";
    mount(true, true);
    fireEvent.click(screen.getByText("Restart mobile tour"));
    expect(within(dialog()).getByText("Phone navigation")).toBeVisible();
    fireEvent.click(within(dialog()).getByText("Skip for now"));
    expect(durable.status).toBe("completed");
    expect(mocks.patch).not.toHaveBeenCalled();
  });
  it("saves contextual tips preference", async () => {
    durable.status = "completed";
    mount();
    const checkbox = await screen.findByRole("checkbox");
    await waitFor(() => expect(checkbox).toBeEnabled());
    fireEvent.click(checkbox);
    await waitFor(() => expect(durable.contextual_tips_enabled).toBe(false));
  });
  it("load failure leaves the workspace usable and never invents completion", async () => {
    mocks.fetch.mockRejectedValue(new Error("offline"));
    mount();
    await screen.findByText("Setup is unavailable. Codexify remains usable.");
    expect(screen.getByText("Usable workspace")).toBeVisible();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(durable.status).toBe("not_started");
  });
  it("failed progress is visible and close remains possible", async () => {
    mount();
    await screen.findByRole("dialog");
    mocks.patch.mockRejectedValue(new Error("Progress was not saved."));
    fireEvent.click(within(dialog()).getByText("Continue"));
    await waitFor(() => expect(within(dialog()).getByRole("alert")).toHaveTextContent("not saved"));
    expect(within(dialog()).getByText("An optional introduction")).toBeVisible();
    fireEvent.click(within(dialog()).getByText("Skip for now"));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByText("Usable workspace")).toBeVisible();
  });
});
