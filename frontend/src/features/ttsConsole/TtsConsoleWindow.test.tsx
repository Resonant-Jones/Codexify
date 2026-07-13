import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TtsConsoleLauncher from "./TtsConsoleLauncher";
import TtsConsoleWindow from "./TtsConsoleWindow";
import type { TtsVoiceProfile } from "./types";

const mockedApi = vi.hoisted(() => ({
  createTtsProfile: vi.fn(),
  deleteTtsProfile: vi.fn(),
  fetchTtsBackends: vi.fn(),
  fetchTtsProfiles: vi.fn(),
  previewTtsProfile: vi.fn(),
  setDefaultTtsProfile: vi.fn(),
  updateTtsProfile: vi.fn(),
}));

vi.mock("./ttsConsoleApi", () => mockedApi);

const baseProfile: TtsVoiceProfile = {
  id: "tts_default",
  name: "Default Voice",
  backend_id: "qwen3_tts",
  is_default: true,
  description: null,
  voice_mode: "preset",
  speaker: "default",
  voice_prompt: "Close mic",
  style_instructions: "Calm",
  language: "english",
  speed: 1,
  temperature: null,
  top_k: null,
  top_p: null,
  repetition_penalty: null,
  max_new_tokens: null,
  do_sample: null,
  backend_params: {},
  reference_audio_asset_id: null,
  reference_text: null,
  x_vector_only_mode: null,
  sample_rate: null,
  output_format: "wav",
  loudness_normalization: null,
  pause_profile: null,
  created_at: "2026-06-08T00:00:00Z",
  updated_at: "2026-06-08T00:00:00Z",
};

beforeEach(() => {
  document.body.innerHTML = "";
  const portalRoot = document.createElement("div");
  portalRoot.id = "cfy-portal-root";
  document.body.appendChild(portalRoot);

  mockedApi.fetchTtsBackends.mockResolvedValue({
    active_backend_id: "qwen3_tts",
    local_only: true,
    items: [
      {
        backend_id: "qwen3_tts",
        display_name: "Qwen3-TTS",
        local_only: true,
        active: true,
        controls: [
          {
            id: "speed",
            label: "Speed",
            type: "number",
            group: "common",
            backend_native: false,
            delivery_control: true,
          },
          {
            id: "temperature",
            label: "Temperature",
            type: "number",
            group: "advanced",
            backend_native: true,
            delivery_control: false,
          },
        ],
      },
    ],
  });
  mockedApi.fetchTtsProfiles.mockResolvedValue({
    items: [baseProfile],
    default_profile_id: baseProfile.id,
  });
  mockedApi.updateTtsProfile.mockImplementation(
    async (_id: string, patch: Partial<TtsVoiceProfile>) => ({
      ...baseProfile,
      ...patch,
    })
  );
  mockedApi.previewTtsProfile.mockResolvedValue({
    profile: baseProfile,
    preview: { render_succeeded: true },
    artifact: {
      output_path: "/tmp/preview.generated.wav",
      media_url: "/api/tts/previews/preview.generated.wav",
      format: "wav",
      bytes_written: 128,
    },
  });
});

describe("TTS Console", () => {
  it("renders the profile list and keeps advanced controls collapsed by default", async () => {
    render(<TtsConsoleWindow open onClose={vi.fn()} />);

    expect(await screen.findByTestId("tts-console-window")).toBeInTheDocument();
    expect(screen.getByTestId("tts-profile-list")).toHaveTextContent(
      "Default Voice"
    );
    await screen.findByTestId("tts-profile-editor");
    expect(screen.getByTestId("tts-console-advanced")).not.toHaveAttribute(
      "open"
    );
  });

  it("marks profile edits dirty and saves through the profile API", async () => {
    const user = userEvent.setup();
    render(<TtsConsoleWindow open onClose={vi.fn()} />);

    const nameInput = await screen.findByLabelText("Profile name");
    await user.clear(nameInput);
    await user.type(nameInput, "Narrator");

    expect(screen.getAllByText("Unsaved changes").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(mockedApi.updateTtsProfile).toHaveBeenCalledWith(
        "tts_default",
        expect.objectContaining({ name: "Narrator" })
      );
    });
  });

  it("calls the preview API from the popup preview panel", async () => {
    const user = userEvent.setup();
    render(<TtsConsoleWindow open onClose={vi.fn()} />);

    await screen.findByTestId("tts-console-window");
    await user.click(screen.getByRole("button", { name: /^preview$/i }));

    await waitFor(() => {
      expect(mockedApi.previewTtsProfile).toHaveBeenCalledWith("tts_default", {
        text: "This is a local Codexify voice preview.",
        format: "wav",
      });
    });
    expect(screen.getByTestId("tts-preview-output")).toHaveTextContent(
      "/tmp/preview.generated.wav"
    );
  });

  it("renders into the app portal root and closes on Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<TtsConsoleWindow open onClose={onClose} />);

    const consoleWindow = await screen.findByTestId("tts-console-window");
    expect(document.getElementById("cfy-portal-root")).toContainElement(consoleWindow);

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("keeps tuning controls out of the launcher surface until opened", () => {
    render(<TtsConsoleLauncher className="pill-tab" />);

    expect(screen.getByRole("button", { name: /tts console/i })).toBeVisible();
    expect(screen.queryByTestId("tts-console-window")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/temperature/i)).not.toBeInTheDocument();
  });
});
