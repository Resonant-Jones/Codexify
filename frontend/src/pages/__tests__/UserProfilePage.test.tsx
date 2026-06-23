import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";
import * as personaSettingsApi from "@/features/settings/api/persona";
import * as personaStudioApi from "@/features/personaStudio/personaStudioApi";
import api from "@/lib/api";
import {
  __resetAuthStateForTests,
  __setAuthStateForTests,
} from "@/lib/authState";

vi.mock("@/components/DocumentGenModal", () => ({
  default: () => null,
}));

vi.mock("@/components/persona/layout/AppShell", () => ({
  default: () => <div data-testid="app-shell-mock" />,
}));

const getUserProfileSpy = vi.spyOn(api, "get");
const updateUserProfileSpy = vi.spyOn(api, "patch");
const updatePersonaSettingsSpy = vi.spyOn(
  personaSettingsApi,
  "updatePersonaSettings"
);
const fetchPersonaSettingsSpy = vi.spyOn(
  personaSettingsApi,
  "fetchPersonaSettings"
);
const fetchPersonaProfilesSpy = vi.spyOn(
  personaStudioApi,
  "fetchPersonaProfiles"
);
const fetchPersonaProfileSpy = vi.spyOn(
  personaStudioApi,
  "fetchPersonaProfile"
);
const createPersonaProfileSpy = vi.spyOn(
  personaStudioApi,
  "createPersonaProfile"
);
const updatePersonaProfileSpy = vi.spyOn(
  personaStudioApi,
  "updatePersonaProfile"
);

function setAuthenticatedProfileRoute(pathname = "/profile") {
  window.history.pushState({}, "", pathname);
  __setAuthStateForTests({
    ready: true,
    status: "authenticated",
    token: "session-token",
  });
}

function mockProfileResponse(profile: Record<string, unknown>) {
  getUserProfileSpy.mockResolvedValueOnce({
    data: {
      ok: true,
      profile,
    },
  } as never);
}

function mockSaveResponse(profile: Record<string, unknown>) {
  updateUserProfileSpy.mockResolvedValueOnce({
    data: {
      ok: true,
      profile,
    },
  } as never);
}

describe("UserProfilePage", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
    vi.clearAllMocks();
    __resetAuthStateForTests();
    setAuthenticatedProfileRoute("/profile");
  });

  it("user_profile_page_loads_current_profile", async () => {
    mockProfileResponse({
      user_id: "acct-123",
      display_name: "Atlas",
      avatar_url: "https://example.com/avatar.png",
      timezone: "America/New_York",
      created_at: "2026-06-22T10:00:00Z",
      updated_at: "2026-06-22T10:01:00Z",
    });

    const { default: UserProfilePage } = await import("../userProfile/UserProfilePage");

    render(<UserProfilePage />);

    expect(
      screen.getByRole("heading", { name: "User Profile" })
    ).toBeInTheDocument();

    expect(
      await screen.findByDisplayValue("Atlas")
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("https://example.com/avatar.png")).toBeInTheDocument();
    expect(screen.getByDisplayValue("America/New_York")).toBeInTheDocument();
    expect(getUserProfileSpy).toHaveBeenCalledWith("/api/user/profile");
  });

  it("user_profile_page_saves_metadata_only", async () => {
    const user = userEvent.setup();
    mockProfileResponse({
      user_id: "acct-123",
      display_name: "Atlas",
      avatar_url: "https://example.com/avatar.png",
      timezone: "America/New_York",
      created_at: "2026-06-22T10:00:00Z",
      updated_at: "2026-06-22T10:01:00Z",
    });
    mockSaveResponse({
      user_id: "acct-123",
      display_name: "Atlas Prime",
      avatar_url: "https://example.com/avatar-2.png",
      timezone: "America/Los_Angeles",
      created_at: "2026-06-22T10:00:00Z",
      updated_at: "2026-06-22T10:02:00Z",
    });

    const { default: UserProfilePage } = await import("../userProfile/UserProfilePage");

    render(<UserProfilePage />);

    await screen.findByDisplayValue("Atlas");

    await user.clear(screen.getByLabelText("Display name"));
    await user.type(screen.getByLabelText("Display name"), "Atlas Prime");
    await user.clear(screen.getByLabelText("Avatar URL"));
    await user.type(
      screen.getByLabelText("Avatar URL"),
      "https://example.com/avatar-2.png"
    );
    await user.clear(screen.getByLabelText("Timezone"));
    await user.type(screen.getByLabelText("Timezone"), "America/Los_Angeles");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() => {
      expect(updateUserProfileSpy).toHaveBeenCalledWith("/api/user/profile", {
        display_name: "Atlas Prime",
        avatar_url: "https://example.com/avatar-2.png",
        timezone: "America/Los_Angeles",
      });
    });
    expect(await screen.findByText("Profile saved.")).toBeInTheDocument();
  });

  it("user_profile_page_does_not_render_canonical_identity_fields", async () => {
    mockProfileResponse({
      user_id: "acct-123",
      display_name: "Atlas",
      avatar_url: null,
      timezone: null,
      created_at: "2026-06-22T10:00:00Z",
      updated_at: "2026-06-22T10:01:00Z",
    });

    const { default: UserProfilePage } = await import("../userProfile/UserProfilePage");

    render(<UserProfilePage />);

    await screen.findByDisplayValue("Atlas");

    expect(screen.queryByLabelText(/id$/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/user id/i)).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/canonical user id/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/authenticated principal id/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/persona profile id/i)
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/api key/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/session token/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/provider credentials/i)
    ).not.toBeInTheDocument();
  });

  it("user_profile_page_does_not_call_persona_profile_api", async () => {
    const user = userEvent.setup();
    mockProfileResponse({
      user_id: "acct-123",
      display_name: "Atlas",
      avatar_url: null,
      timezone: null,
      created_at: "2026-06-22T10:00:00Z",
      updated_at: "2026-06-22T10:01:00Z",
    });
    mockSaveResponse({
      user_id: "acct-123",
      display_name: "Atlas Prime",
      avatar_url: null,
      timezone: null,
      created_at: "2026-06-22T10:00:00Z",
      updated_at: "2026-06-22T10:02:00Z",
    });

    const { default: UserProfilePage } = await import("../userProfile/UserProfilePage");

    render(<UserProfilePage />);

    await screen.findByDisplayValue("Atlas");
    await user.clear(screen.getByLabelText("Display name"));
    await user.type(screen.getByLabelText("Display name"), "Atlas Prime");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(updatePersonaSettingsSpy).not.toHaveBeenCalled();
    expect(fetchPersonaSettingsSpy).not.toHaveBeenCalled();
    expect(fetchPersonaProfilesSpy).not.toHaveBeenCalled();
    expect(fetchPersonaProfileSpy).not.toHaveBeenCalled();
    expect(createPersonaProfileSpy).not.toHaveBeenCalled();
    expect(updatePersonaProfileSpy).not.toHaveBeenCalled();
  });

  it("user_profile_page_shows_generic_non_secret_error", async () => {
    getUserProfileSpy.mockRejectedValueOnce(
      new Error("backend exploded with session-token and x-api-key")
    );

    const { default: UserProfilePage } = await import("../userProfile/UserProfilePage");

    render(<UserProfilePage />);

    expect(
      await screen.findByRole("alert")
    ).toHaveTextContent("Unable to load user profile. Please try again.");
    expect(screen.queryByText(/session-token/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/x-api-key/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/stack trace/i)).not.toBeInTheDocument();
  });

  it("user_profile_route_is_registered", async () => {
    mockProfileResponse({
      user_id: "acct-123",
      display_name: "Atlas",
      avatar_url: null,
      timezone: null,
      created_at: "2026-06-22T10:00:00Z",
      updated_at: "2026-06-22T10:01:00Z",
    });
    window.history.pushState({}, "", "/profile");

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "User Profile" })
    ).toBeInTheDocument();
    expect(screen.queryByTestId("app-shell-mock")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(getUserProfileSpy).toHaveBeenCalledWith("/api/user/profile");
    });
  });
});
