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

export type SlashCommandDefinition = {
  id: SlashCommandId;
  label: string;
  description: string;
  aliases: readonly string[];
  keywords: readonly string[];
  scaffold: string;
};

export const SLASH_COMMANDS = [
  {
    id: "thread",
    label: "Thread",
    description: "Start or switch a conversation thread.",
    aliases: ["chat", "conversation"],
    keywords: ["reply", "turn"],
    scaffold: "/thread",
  },
  {
    id: "doc",
    label: "Document",
    description: "Add or reference a document.",
    aliases: ["do", "docs", "document"],
    keywords: ["file", "note", "reference"],
    scaffold: "/doc",
  },
  {
    id: "project",
    label: "Project",
    description: "Scope the request to a project.",
    aliases: ["workspace", "repo"],
    keywords: ["scope", "context"],
    scaffold: "/project",
  },
  {
    id: "workspace",
    label: "Workspace",
    description: "Work across the current workspace.",
    aliases: ["root", "local"],
    keywords: ["folder", "environment"],
    scaffold: "/workspace",
  },
  {
    id: "profile",
    label: "Profile",
    description: "Choose an identity or persona.",
    aliases: ["identity", "persona", "account"],
    keywords: ["user", "role"],
    scaffold: "/profile",
  },
  {
    id: "flow",
    label: "Flow",
    description: "Switch to a workflow step.",
    aliases: ["pipeline", "sequence"],
    keywords: ["process", "mode"],
    scaffold: "/flow",
  },
  {
    id: "secure",
    label: "Secure",
    description: "Tighten access or permissions.",
    aliases: ["permission", "lock"],
    keywords: ["privacy", "acl"],
    scaffold: "/secure",
  },
  {
    id: "connect",
    label: "Connect",
    description: "Link sources or peers.",
    aliases: ["sync", "attach"],
    keywords: ["bridge", "federate"],
    scaffold: "/connect",
  },
  {
    id: "help",
    label: "Help",
    description: "Show command help.",
    aliases: ["?", "commands"],
    keywords: ["guide", "menu"],
    scaffold: "/help",
  },
] as const satisfies readonly SlashCommandDefinition[];

export const SLASH_COMMAND_LOOKUP = Object.fromEntries(
  SLASH_COMMANDS.map((command) => [command.id, command])
) as Record<SlashCommandId, SlashCommandDefinition>;
