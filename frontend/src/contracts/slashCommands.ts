import { z } from "zod";

const intentKind = z.enum([
  "conversation", "knowledge", "workspace", "automation",
  "security", "integration", "codex", "help",
]);
const retrievalHint = z.enum(["none", "conversation", "project", "personal_knowledge"]);
const effects = z.object({ intentKind, retrievalHint });
const commandDefinition = z.object({
  id: z.string().min(1),
  token: z.string().regex(/^\/[^/\s]+$/),
  label: z.string().min(1),
  description: z.string().min(1),
  aliases: z.array(z.string().regex(/^[^/\s]+$/)),
  keywords: z.array(z.string().min(1)),
  scaffold: z.string().min(1),
  interactionModes: z.array(z.string().min(1)).min(1),
  effects: effects.nullable(),
  availability: z.enum(["available", "unavailable", "unknown"]),
  availabilityReason: z.string().min(1).nullable(),
}).refine((command) =>
  !command.interactionModes.includes("chat_intent") || command.effects !== null
);
const manifest = z.object({
  schemaVersion: z.literal(1),
  manifestRevision: z.string().min(1),
  commands: z.array(commandDefinition),
});

export type SlashCommandIntentKind = z.infer<typeof intentKind>;
export type SlashCommandRetrievalHint = z.infer<typeof retrievalHint>;
export type SlashCommandEffects = z.infer<typeof effects>;
export type SlashCommandDefinition = z.infer<typeof commandDefinition>;
export type SlashCommandManifest = z.infer<typeof manifest>;

export function decodeSlashCommandManifest(value: unknown): SlashCommandManifest {
  const decoded = manifest.parse(value);
  const ids = new Set<string>();
  const tokens = new Set<string>();
  const aliases = new Set<string>();
  for (const command of decoded.commands) {
    const token = normalizeSlashToken(command.token);
    if (ids.has(command.id) || tokens.has(token)) {
      throw new Error("Duplicate slash command identity");
    }
    ids.add(command.id);
    tokens.add(token);
    for (const alias of command.aliases.map(normalizeSlashToken)) {
      if (aliases.has(alias)) throw new Error("Ambiguous slash command alias");
      aliases.add(alias);
    }
  }
  return decoded;
}

export function resolveSlashCommand(
  commands: readonly SlashCommandDefinition[],
  token: string
): SlashCommandDefinition | undefined {
  const normalized = normalizeSlashToken(token);
  if (!normalized) return undefined;
  return commands.find((command) => normalizeSlashToken(command.token) === normalized)
    ?? commands.find((command) =>
      command.aliases.some((alias) => normalizeSlashToken(alias) === normalized)
    );
}

export function filterSlashCommands(
  commands: readonly SlashCommandDefinition[],
  query: string
): readonly SlashCommandDefinition[] {
  const normalized = normalizeSlashToken(query);
  if (!normalized) return commands;
  const exact = resolveSlashCommand(commands, normalized);
  if (exact) return [exact];

  const tokens: SlashCommandDefinition[] = [];
  const aliases: SlashCommandDefinition[] = [];
  const keywords: SlashCommandDefinition[] = [];
  for (const command of commands) {
    if (normalizeSlashToken(command.token).startsWith(normalized)) tokens.push(command);
    else if (command.aliases.some((alias) => normalizeSlashToken(alias).startsWith(normalized))) aliases.push(command);
    else if (command.keywords.some((keyword) => keyword.toLowerCase().startsWith(normalized))) keywords.push(command);
  }
  return [...tokens, ...aliases, ...keywords];
}

export type SlashCommandIntent = {
  command: SlashCommandDefinition & { effects: SlashCommandEffects };
  rawToken: string;
  queryText: string;
};

export type SlashCommandContextDirectiveKind = "connector_context";

export type SlashCommandContextDirective = {
  kind: SlashCommandContextDirectiveKind;
  connectorId: "obsidian";
  invocation: "turn_scoped";
  queryText: string;
};

export type SlashCommandIntentPayload = {
  intentKind: SlashCommandIntentKind;
  retrievalHint?: SlashCommandRetrievalHint;
  commandId?: string;
  rawInput: string;
  queryText?: string;
  contextDirectives?: SlashCommandContextDirective[];
};

function normalizeSlashToken(value: string): string {
  return value.trim().replace(/^\/+/, "").toLowerCase();
}

export function resolveSlashCommandIntent(
  input: string,
  commands: readonly SlashCommandDefinition[]
): SlashCommandIntent | null {
  const normalizedInput = input.trimEnd();
  if (!normalizedInput) return null;

  let slashIndex = -1;
  for (let index = normalizedInput.length - 1; index >= 0; index -= 1) {
    if (normalizedInput[index] !== "/") continue;
    if (index > 0 && !/\s/.test(normalizedInput[index - 1])) continue;
    slashIndex = index;
    break;
  }

  if (slashIndex < 0) return null;

  const rawSegment = normalizedInput.slice(slashIndex).trimEnd();
  if (!rawSegment.startsWith("/")) return null;

  const body = rawSegment.slice(1).trimStart();
  if (!body) return null;

  const firstWhitespaceIndex = body.search(/\s/);
  const commandToken =
    firstWhitespaceIndex === -1 ? body : body.slice(0, firstWhitespaceIndex);
  const normalizedToken = normalizeSlashToken(commandToken);
  if (!normalizedToken) return null;

  const command = resolveSlashCommand(commands, normalizedToken);
  if (!command?.interactionModes.includes("chat_intent") ||
      !command.effects || command.availability === "unavailable") return null;

  const queryText =
    firstWhitespaceIndex === -1 ? "" : body.slice(firstWhitespaceIndex).trimStart();

  return {
    command: { ...command, effects: command.effects },
    rawToken: `/${normalizedToken}`,
    queryText,
  };
}

export function buildSlashCommandIntentPayload(
  input: string,
  commands: readonly SlashCommandDefinition[]
): SlashCommandIntentPayload | null {
  const intent = resolveSlashCommandIntent(input, commands);
  if (!intent) return null;

  const payload: SlashCommandIntentPayload = {
    commandId: intent.command.id,
    intentKind: intent.command.effects.intentKind,
    retrievalHint: intent.command.effects.retrievalHint,
    rawInput: input,
  };

  const trimmedQueryText = intent.queryText.trim();
  if (intent.command.id !== "obsidian" || trimmedQueryText.length === 0) {
    return payload;
  }

  return {
    ...payload,
    queryText: trimmedQueryText,
    contextDirectives: [
      {
        kind: "connector_context",
        connectorId: "obsidian",
        invocation: "turn_scoped",
        queryText: trimmedQueryText,
      },
    ],
  };
}

export function buildSlashCommandSendPayload(
  input: string,
  commands: readonly SlashCommandDefinition[]
): {
  messageText: string;
  slashIntent: SlashCommandIntentPayload | null;
} {
  const slashIntent = buildSlashCommandIntentPayload(input, commands);
  if (!slashIntent) {
    return {
      messageText: input,
      slashIntent: null,
    };
  }

  if (slashIntent.commandId !== "obsidian") {
    return {
      messageText: input,
      slashIntent,
    };
  }

  const trimmedQueryText = slashIntent.queryText?.trim() ?? "";
  if (!trimmedQueryText) {
    return {
      messageText: input,
      slashIntent,
    };
  }

  return {
    messageText: trimmedQueryText,
    slashIntent,
  };
}
