export type SlashCommandId =
  | "thread"
  | "doc"
  | "project"
  | "workspace"
  | "profile"
  | "flow"
  | "secure"
  | "connect"
  | "help";

export type SlashCommandIntentKind =
  | "conversation"
  | "knowledge"
  | "workspace"
  | "automation"
  | "security"
  | "integration"
  | "help";

export type SlashCommandRetrievalHint =
  | "none"
  | "conversation"
  | "project"
  | "personal_knowledge";

export type SlashCommandEffects = {
  intentKind: SlashCommandIntentKind;
  retrievalHint: SlashCommandRetrievalHint;
};

export type SlashCommandDefinition = {
  id: SlashCommandId;
  label: string;
  description: string;
  aliases: readonly string[];
  keywords: readonly string[];
  scaffold: string;
  effects: SlashCommandEffects;
};

export const SLASH_COMMANDS = [
  {
    id: "thread",
    label: "Thread",
    description: "Start or switch a conversation thread.",
    aliases: ["chat", "conversation"],
    keywords: ["reply", "turn"],
    scaffold: "/thread",
    effects: {
      intentKind: "conversation",
      retrievalHint: "conversation",
    },
  },
  {
    id: "doc",
    label: "Document",
    description: "Add or reference a document.",
    aliases: ["do", "docs", "document"],
    keywords: ["file", "note", "reference"],
    scaffold: "/doc",
    effects: {
      intentKind: "knowledge",
      retrievalHint: "personal_knowledge",
    },
  },
  {
    id: "project",
    label: "Project",
    description: "Scope the request to a project.",
    aliases: ["workspace", "repo"],
    keywords: ["scope", "context"],
    scaffold: "/project",
    effects: {
      intentKind: "workspace",
      retrievalHint: "project",
    },
  },
  {
    id: "workspace",
    label: "Workspace",
    description: "Work across the current workspace.",
    aliases: ["root", "local"],
    keywords: ["folder", "environment"],
    scaffold: "/workspace",
    effects: {
      intentKind: "workspace",
      retrievalHint: "project",
    },
  },
  {
    id: "profile",
    label: "Profile",
    description: "Choose an identity or persona.",
    aliases: ["identity", "persona", "account"],
    keywords: ["user", "role"],
    scaffold: "/profile",
    effects: {
      intentKind: "conversation",
      retrievalHint: "none",
    },
  },
  {
    id: "flow",
    label: "Flow",
    description: "Switch to a workflow step.",
    aliases: ["pipeline", "sequence"],
    keywords: ["process", "mode"],
    scaffold: "/flow",
    effects: {
      intentKind: "automation",
      retrievalHint: "none",
    },
  },
  {
    id: "secure",
    label: "Secure",
    description: "Tighten access or permissions.",
    aliases: ["permission", "lock"],
    keywords: ["privacy", "acl"],
    scaffold: "/secure",
    effects: {
      intentKind: "security",
      retrievalHint: "none",
    },
  },
  {
    id: "connect",
    label: "Connect",
    description: "Link sources or peers.",
    aliases: ["sync", "attach"],
    keywords: ["bridge", "federate"],
    scaffold: "/connect",
    effects: {
      intentKind: "integration",
      retrievalHint: "none",
    },
  },
  {
    id: "help",
    label: "Help",
    description: "Show command help.",
    aliases: ["?", "commands"],
    keywords: ["guide", "menu"],
    scaffold: "/help",
    effects: {
      intentKind: "help",
      retrievalHint: "none",
    },
  },
] as const satisfies readonly SlashCommandDefinition[];

export const SLASH_COMMAND_LOOKUP = Object.fromEntries(
  SLASH_COMMANDS.map((command) => [command.id, command])
) as Record<SlashCommandId, SlashCommandDefinition>;

export const SLASH_COMMAND_TOKEN_LOOKUP = Object.fromEntries(
  SLASH_COMMANDS.flatMap((command) => [
    [command.id, command],
    ...command.aliases.map((alias) => [alias, command] as const),
  ])
) as Record<string, SlashCommandDefinition>;

export type SlashCommandIntent = {
  command: SlashCommandDefinition;
  rawToken: string;
  queryText: string;
};

export type SlashCommandIntentPayload = {
  commandId: SlashCommandId;
  rawToken: string;
  queryText: string;
  intentKind: SlashCommandIntentKind;
  retrievalHint: SlashCommandRetrievalHint;
};

function normalizeSlashToken(value: string): string {
  return value.trim().replace(/^\/+/, "").toLowerCase();
}

export function resolveSlashCommandIntent(
  input: string
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

  const command = SLASH_COMMAND_TOKEN_LOOKUP[normalizedToken];
  if (!command) return null;

  const queryText =
    firstWhitespaceIndex === -1 ? "" : body.slice(firstWhitespaceIndex).trimStart();

  return {
    command,
    rawToken: `/${normalizedToken}`,
    queryText,
  };
}

export function buildSlashCommandIntentPayload(
  input: string
): SlashCommandIntentPayload | null {
  const intent = resolveSlashCommandIntent(input);
  if (!intent) return null;

  return {
    commandId: intent.command.id,
    rawToken: `/${intent.command.id}`,
    queryText: intent.queryText,
    intentKind: intent.command.effects.intentKind,
    retrievalHint: intent.command.effects.retrievalHint,
  };
}
