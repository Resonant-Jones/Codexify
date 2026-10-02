import type { PersonaProfileDraft } from "../personaStudioStore";

export type PersonaStudioConfiguratorSection =
  | "prompt"
  | "model"
  | "voice"
  | "capabilities"
  | "retrieval";

export type PersonaStudioConfiguratorChange = {
  fieldPath: string;
  label: string;
  section: PersonaStudioConfiguratorSection;
};

export type PersonaStudioConfiguratorResult = {
  draft: PersonaProfileDraft;
  changes: PersonaStudioConfiguratorChange[];
  changedFieldPaths: string[];
  sections: PersonaStudioConfiguratorSection[];
  recognized: boolean;
};

function cloneDraft(profile: PersonaProfileDraft): PersonaProfileDraft {
  return JSON.parse(JSON.stringify(profile)) as PersonaProfileDraft;
}

function getValue(
  profile: PersonaProfileDraft,
  fieldPath: string
): unknown {
  switch (fieldPath) {
    case "prompt.styleNotes":
      return profile.config.prompt.styleNotes;
    case "prompt.directives":
      return profile.config.prompt.directives;
    case "model.provider":
      return profile.config.model.provider;
    case "model.model":
      return profile.config.model.model;
    case "model.temperature":
      return profile.config.model.temperature;
    case "capabilities.permissions.web":
      return profile.config.tools.permissions.web;
    case "capabilities.permissions.email":
      return profile.config.tools.permissions.email;
    case "voice.enabled":
      return profile.config.voice.enabled;
    case "retrieval.enabled":
      return profile.config.retrieval.enabled;
    default:
      return undefined;
  }
}

function setValue(
  profile: PersonaProfileDraft,
  fieldPath: string,
  value: unknown
): void {
  switch (fieldPath) {
    case "prompt.styleNotes":
      profile.config.prompt.styleNotes = value as string;
      return;
    case "prompt.directives":
      profile.config.prompt.directives = value as string;
      return;
    case "model.provider":
      profile.config.model.provider = value as string;
      return;
    case "model.model":
      profile.config.model.model = value as string;
      return;
    case "model.temperature":
      profile.config.model.temperature = value as number;
      return;
    case "capabilities.permissions.web":
      profile.config.tools.permissions.web = value as boolean;
      return;
    case "capabilities.permissions.email":
      profile.config.tools.permissions.email = value as boolean;
      return;
    case "voice.enabled":
      profile.config.voice.enabled = value as boolean;
      return;
    case "retrieval.enabled":
      profile.config.retrieval.enabled = value as boolean;
      return;
  }
}

/**
 * The approved V2 prototype's deliberately narrow local configurator.
 *
 * This module is intentionally pure: it accepts one draft and one text input,
 * returns a replacement draft plus an auditable change receipt, and never
 * reaches chat, providers, storage, or the Persona Profile API.
 */
export function applyPersonaStudioConfiguratorIntent(
  profile: PersonaProfileDraft,
  input: string
): PersonaStudioConfiguratorResult {
  const draft = cloneDraft(profile);
  const text = input.toLowerCase();
  const changes: PersonaStudioConfiguratorChange[] = [];

  const apply = (
    fieldPath: string,
    value: unknown,
    label: string,
    section: PersonaStudioConfiguratorSection
  ) => {
    if (JSON.stringify(getValue(draft, fieldPath)) === JSON.stringify(value)) {
      return;
    }

    setValue(draft, fieldPath, value);
    changes.push({ fieldPath, label, section });
  };

  // Preserve the prototype's recognition order, patterns, mappings, and
  // neutral behavior for requests it cannot safely map to typed draft fields.
  if (/analytical|more rigorous|evidence|precise/.test(text)) {
    apply(
      "prompt.styleNotes",
      "Analytical, evidence-led, concise. Surface assumptions and tradeoffs.",
      "Behavior shifted toward analytical and evidence-led",
      "prompt"
    );
    apply(
      "prompt.directives",
      "Separate evidence from inference. Stress-test assumptions. Prefer the smallest useful next step.",
      "Analytical directives strengthened",
      "prompt"
    );
  }
  if (/claude|anthropic/.test(text)) {
    apply("model.provider", "anthropic", "Provider set to Anthropic", "model");
    apply("model.model", "claude-sonnet", "Model set to Claude Sonnet", "model");
  }
  if (/openai|gpt/.test(text) && !/not openai|instead of openai/.test(text)) {
    apply("model.provider", "openai", "Provider set to OpenAI", "model");
    apply("model.model", "gpt-5", "Model set to GPT-5", "model");
  }
  if (/lower temperature|low temperature|less creative|more deterministic/.test(text)) {
    apply("model.temperature", 0.2, "Temperature lowered to 0.20", "model");
  }
  if (/higher temperature|more creative|imaginative/.test(text)) {
    apply("model.temperature", 0.9, "Temperature raised to 0.90", "model");
  }
  if (/(allow|enable|turn on|use).{0,18}(web|web search)|web search.{0,12}(on|enabled|allowed)/.test(text)) {
    apply(
      "capabilities.permissions.web",
      true,
      "Web search requested",
      "capabilities"
    );
  }
  if (/(disable|turn off|remove|no).{0,18}(web|web search)/.test(text)) {
    apply(
      "capabilities.permissions.web",
      false,
      "Web search disabled",
      "capabilities"
    );
  }
  if (/(disable|turn off|remove|no).{0,18}email|email.{0,12}(off|disabled)/.test(text)) {
    apply(
      "capabilities.permissions.email",
      false,
      "Email disabled",
      "capabilities"
    );
  }
  if (/(allow|enable|turn on|use).{0,18}email|email.{0,12}(on|enabled|allowed)/.test(text)) {
    apply(
      "capabilities.permissions.email",
      true,
      "Email requested",
      "capabilities"
    );
  }
  if (/(disable|turn off).{0,18}voice/.test(text)) {
    apply("voice.enabled", false, "Voice disabled", "voice");
  }
  if (/(enable|turn on).{0,18}voice/.test(text)) {
    apply("voice.enabled", true, "Voice enabled", "voice");
  }
  if (/warmer|more empathetic|more human/.test(text)) {
    apply(
      "prompt.styleNotes",
      "Warm, grounded, and analytical. Acknowledge context before recommending action.",
      "Tone made warmer and more grounded",
      "prompt"
    );
  }
  if (/(disable|turn off).{0,18}retrieval/.test(text)) {
    apply("retrieval.enabled", false, "Retrieval disabled", "retrieval");
  }
  if (/(enable|turn on|use).{0,18}retrieval/.test(text)) {
    apply("retrieval.enabled", true, "Retrieval enabled", "retrieval");
  }

  const changedFieldPaths = changes.map((change) => change.fieldPath);
  const sections = Array.from(new Set(changes.map((change) => change.section)));

  return {
    draft,
    changes,
    changedFieldPaths,
    sections,
    recognized: changes.length > 0,
  };
}
