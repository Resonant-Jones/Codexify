import type { PersonaConfig } from "../personaStudioStore";

export type StudioGuideSeverity = "warning" | "info";

export type StudioGuideCard = {
  id: string;
  title: string;
  summary: string;
  suggestion: string;
  question?: string;
  evidence: string[];
  severity: StudioGuideSeverity;
};

const ROLE_CUES = [
  "you are",
  "act as",
  "serve as",
  "role",
  "persona",
  "guide",
  "coach",
  "assistant",
  "partner",
  "advisor",
];

const VAGUE_PROMPT_CUES = [
  "be helpful",
  "helpful assistant",
  "help the user",
  "assist the user",
  "support the user",
  "answer questions",
];

const CONSTRAINT_CUES = [
  "never",
  "must",
  "only",
  "avoid",
  "do not",
  "don't",
  "limit",
  "prefer",
  "unless",
];

const CONTRADICTION_PAIRS = [
  {
    id: "tone-warm-cold",
    title: "Contradictory tone instructions",
    positive: ["warm", "welcoming", "friendly"],
    negative: ["cold", "distant", "flat"],
    summary:
      "The draft asks for opposite emotional signals, which makes the tone hard to follow.",
    suggestion:
      "Pick one temperature and let the rest of the wording support it. For example, keep the tone warm and remove the cold language.",
    question: "Which tone should win when the instructions collide?",
    evidenceLabel: "warm/cold",
  },
  {
    id: "tone-concise-verbose",
    title: "Contradictory tone instructions",
    positive: ["concise", "brief", "succinct"],
    negative: ["verbose", "detailed", "expansive"],
    summary:
      "The draft asks the persona to be both compressed and expansive at the same time.",
    suggestion:
      "Choose the level of detail you actually want and remove the opposite instruction.",
    question: "Should the persona optimize for brevity or explanation depth?",
    evidenceLabel: "concise/verbose",
  },
  {
    id: "tone-formal-casual",
    title: "Contradictory tone instructions",
    positive: ["formal", "professional"],
    negative: ["casual", "relaxed", "laid-back"],
    summary:
      "The draft mixes formal and casual cues without saying which one should dominate.",
    suggestion:
      "Keep the dominant tone explicit and let secondary flavor stay subordinate to it.",
    question: "Do you want a formal register, a casual one, or a deliberate blend?",
    evidenceLabel: "formal/casual",
  },
];

function normalizeText(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function hasAny(text: string, terms: string[]): boolean {
  return terms.some((term) => text.includes(term));
}

function words(value: string): string[] {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/g)
    .filter((token) => token.length > 3);
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}

function analyzeRoleClarity(
  systemPrompt: string,
  identityName: string,
  identityDescription: string
): StudioGuideCard | null {
  const normalized = normalizeText(systemPrompt);
  const hasCue = hasAny(normalized, ROLE_CUES);

  if (normalized.length >= 80 && hasCue) {
    return null;
  }

  const identityHint = [identityName, identityDescription]
    .map(normalizeText)
    .filter(Boolean)
    .join(" ");

  return {
    id: "role-clarity",
    title: "Role clarity",
    summary:
      "The draft does not clearly pin down the persona's role, audience, and job to be done.",
    suggestion:
      "Open with a direct role statement. A simple pattern is: 'You are a [role] for [audience], and your job is to [outcome].'",
    question:
      identityHint ? "Who is this persona for, and what should it help with first?" : "What role should this persona own?",
    evidence: normalized ? [systemPrompt.trim()] : ["system prompt is empty"],
    severity: "warning",
  };
}

function analyzeVagueness(systemPrompt: string): StudioGuideCard | null {
  const normalized = normalizeText(systemPrompt);

  if (normalized.length >= 80 && !hasAny(normalized, VAGUE_PROMPT_CUES)) {
    return null;
  }

  return {
    id: "vague-system-prompt",
    title: "System prompt is too vague",
    summary:
      "The system prompt reads like a placeholder instead of a specific operating contract.",
    suggestion:
      "Add the persona's scope, the kinds of outputs it should favor, and the boundaries it must not cross.",
    question: "What should this persona reliably do that a generic assistant would not?",
    evidence: normalized ? [systemPrompt.trim()] : ["system prompt is empty"],
    severity: "warning",
  };
}

function analyzeConstraints(directives: string): StudioGuideCard | null {
  const normalized = normalizeText(directives);
  if (normalized && hasAny(normalized, CONSTRAINT_CUES)) {
    return null;
  }

  return {
    id: "missing-constraints",
    title: "Missing constraints",
    summary:
      "The draft does not include any hard constraints to keep behavior bounded.",
    suggestion:
      "Add a small set of firm limits, such as privacy boundaries, refusal rules, or format constraints.",
    question: "Which rules should always win, even when the prompt gets ambiguous?",
    evidence: normalized ? [directives.trim()] : ["directives are empty"],
    severity: "warning",
  };
}

function analyzeToneContradictions(
  systemPrompt: string,
  styleNotes: string,
  directives: string
): StudioGuideCard | null {
  const normalized = normalizeText([systemPrompt, styleNotes, directives].filter(Boolean).join(" "));

  for (const pair of CONTRADICTION_PAIRS) {
    const positive = hasAny(normalized, pair.positive);
    const negative = hasAny(normalized, pair.negative);
    if (positive && negative) {
      return {
        id: pair.id,
        title: pair.title,
        summary: pair.summary,
        suggestion: pair.suggestion,
        question: pair.question,
        evidence: [pair.evidenceLabel],
        severity: "warning",
      };
    }
  }

  return null;
}

function analyzeIdentityMismatch(
  identityName: string,
  identityDescription: string,
  systemPrompt: string,
  styleNotes: string,
  directives: string
): StudioGuideCard | null {
  const identityTokens = unique(
    [...words(identityName), ...words(identityDescription)].filter(
      (token) =>
        ![
          "persona",
          "assistant",
          "assistance",
          "default",
          "profile",
          "persona",
          "specialized",
          "focused",
          "support",
          "helper",
          "guidance",
          "general",
        ].includes(token)
    )
  );

  if (identityTokens.length === 0) {
    return null;
  }

  const combinedText = normalizeText([systemPrompt, styleNotes, directives].filter(Boolean).join(" "));
  const missingTokens = identityTokens.filter((token) => !combinedText.includes(token));

  if (missingTokens.length < 2) {
    return null;
  }

  return {
    id: "identity-mismatch",
    title: "Identity and wording mismatch",
    summary:
      "The persona identity points in one direction, but the draft wording does not echo those signals yet.",
    suggestion:
      "Repeat the identity's core nouns in the system prompt or style notes so the draft can stay aligned with the intended role.",
    question: `Should the draft emphasize ${missingTokens.slice(0, 3).join(", ")} specifically?`,
    evidence: missingTokens.slice(0, 3),
    severity: "info",
  };
}

export function analyzeStudioGuideDraft(
  config: PersonaConfig | null
): StudioGuideCard[] {
  if (!config) {
    return [];
  }

  const cards = [
    analyzeRoleClarity(
      config.prompt.systemPrompt,
      config.identity.name,
      config.identity.description
    ),
    analyzeVagueness(config.prompt.systemPrompt),
    analyzeToneContradictions(
      config.prompt.systemPrompt,
      config.prompt.styleNotes,
      config.prompt.directives
    ),
    analyzeConstraints(config.prompt.directives),
    analyzeIdentityMismatch(
      config.identity.name,
      config.identity.description,
      config.prompt.systemPrompt,
      config.prompt.styleNotes,
      config.prompt.directives
    ),
  ];

  return cards.filter((card): card is StudioGuideCard => Boolean(card));
}
