import { describe, expect, it } from "vitest";

import { applyPersonaStudioConfiguratorIntent } from "../lib/personaStudioConfigurator";
import { createPersonaStudioSeedState } from "../personaStudioStore";

describe("Persona Studio deterministic configurator", () => {
  it("preserves the approved prototype mappings as a pure local draft transform", () => {
    const profile = createPersonaStudioSeedState().profiles[0];
    profile.config.tools.permissions.web = false;
    profile.config.voice.enabled = false;
    profile.config.retrieval.enabled = false;
    const result = applyPersonaStudioConfiguratorIntent(
      profile,
      "Make this more analytical, use Claude, lower temperature, enable web search and email, turn on voice, and enable retrieval."
    );

    expect(result.recognized).toBe(true);
    expect(result.changedFieldPaths).toEqual(expect.arrayContaining([
      "prompt.styleNotes",
      "prompt.directives",
      "model.provider",
      "model.model",
      "model.temperature",
      "capabilities.permissions.web",
      "capabilities.permissions.email",
      "voice.enabled",
      "retrieval.enabled",
    ]));
    expect(result.draft.config.model).toMatchObject({
      provider: "anthropic",
      model: "claude-sonnet",
      temperature: 0.2,
    });
    expect(result.draft.config.tools.permissions).toMatchObject({ web: true, email: true });
    expect(result.draft.config.voice.enabled).toBe(true);
    expect(result.draft.config.retrieval.enabled).toBe(true);
    expect(profile.config.model.provider).toBe("openai");
  });

  it("does not invent a change for unsupported or explicitly negated requests", () => {
    const profile = createPersonaStudioSeedState().profiles[0];
    const result = applyPersonaStudioConfiguratorIntent(
      profile,
      "Do something mystical instead of OpenAI."
    );

    expect(result).toMatchObject({ recognized: false, changedFieldPaths: [] });
    expect(result.draft).toEqual(profile);
  });
});
