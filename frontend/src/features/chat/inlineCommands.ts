import {
  resolveSlashCommand,
  type SlashCommandDefinition,
} from "@/contracts/slashCommands";

// These IDs identify installed callbacks and option sources.
export type InlineCommandName = "project" | "provider" | "model" | "mode" | "retrieval";

export type InlineCommandOption = {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
  disabledReason?: string;
};

export type InlineCommandDefinition = {
  name: InlineCommandName;
  label: string;
  description: string;
  token: string;
  aliases: readonly string[];
};

export type InlineCommandOptionSets = Partial<
  Record<InlineCommandName, readonly InlineCommandOption[]>
>;

type ParsedCommandBase = {
  draft: string;
  command: InlineCommandDefinition | null;
  commandQuery: string;
  valueQuery: string;
};

export type InlineCommandParseResult =
  | (ParsedCommandBase & {
      state: "incomplete";
      suggestions: readonly InlineCommandDefinition[] | readonly InlineCommandOption[];
    })
  | (ParsedCommandBase & {
      state: "ready";
      command: InlineCommandDefinition;
      option: InlineCommandOption;
      suggestions: readonly InlineCommandOption[];
    })
  | (ParsedCommandBase & {
      state: "executed";
      command: InlineCommandDefinition;
      option: InlineCommandOption;
      confirmation: string;
      suggestions: readonly InlineCommandOption[];
    })
  | (ParsedCommandBase & {
      state: "unknown";
      suggestions: readonly InlineCommandDefinition[] | readonly InlineCommandOption[];
    })
  | (ParsedCommandBase & {
      state: "disabled";
      command: InlineCommandDefinition;
      option: InlineCommandOption;
      reason: string;
      suggestions: readonly InlineCommandOption[];
    })
  | (ParsedCommandBase & {
      state: "ambiguous";
      command: InlineCommandDefinition;
      suggestions: readonly InlineCommandOption[];
    });

const normalizeQuery = (value: string) => value.trim().toLowerCase();

export function getSupportedInlineCommands(
  optionSets: InlineCommandOptionSets,
  commands: readonly SlashCommandDefinition[]
): readonly InlineCommandDefinition[] {
  return commands.flatMap((command) => {
    const name = command.id as InlineCommandName;
    if (
      !command.interactionModes.includes("composer_control") ||
      command.availability === "unavailable" ||
      !Object.prototype.hasOwnProperty.call(optionSets, name) ||
      !optionSets[name]?.length
    ) return [];
    return [{
      name,
      label: command.label,
      description: command.description,
      token: command.token,
      aliases: command.aliases,
    }];
  });
}

export function matchInlineCommandPrefix(
  query: string,
  definitions: readonly InlineCommandDefinition[]
): readonly InlineCommandDefinition[] {
  const normalized = normalizeQuery(query);
  return definitions.filter((definition) =>
    definition.token.slice(1).toLowerCase().startsWith(normalized) ||
    definition.aliases.some((alias) => alias.toLowerCase().startsWith(normalized))
  );
}

export function suggestInlineCommandValues(
  query: string,
  options: readonly InlineCommandOption[]
): readonly InlineCommandOption[] {
  const normalized = normalizeQuery(query);
  if (!normalized) return [...options];
  return options.filter((option) => {
    const value = normalizeQuery(option.value);
    const label = normalizeQuery(option.label);
    return value.includes(normalized) || label.includes(normalized);
  });
}

function unknownResult(
  draft: string,
  commandQuery = "",
  valueQuery = "",
  suggestions: readonly InlineCommandDefinition[] | readonly InlineCommandOption[] = []
): InlineCommandParseResult {
  return {
    state: "unknown",
    draft,
    command: null,
    commandQuery,
    valueQuery,
    suggestions,
  };
}

export function parseInlineCommandDraft(
  draft: string,
  optionSets: InlineCommandOptionSets,
  commands: readonly SlashCommandDefinition[]
): InlineCommandParseResult {
  if (!draft.startsWith("/") || draft.startsWith("//") || draft.includes("\n")) {
    return unknownResult(draft);
  }

  const definitions = getSupportedInlineCommands(optionSets, commands);
  const body = draft.slice(1);
  const whitespaceIndex = body.search(/\s/);
  const commandQuery =
    whitespaceIndex < 0 ? body : body.slice(0, whitespaceIndex);
  const rawValue = whitespaceIndex < 0 ? "" : body.slice(whitespaceIndex + 1);
  const valueQuery = rawValue.trim();
  if (commandQuery.includes("/")) return unknownResult(draft);
  const commandMatches = matchInlineCommandPrefix(commandQuery, definitions);
  const resolved = resolveSlashCommand(commands, commandQuery);
  const exactCommand =
    definitions.find((definition) => definition.name === resolved?.id) ?? null;

  if (!exactCommand) {
    if (commandMatches.length > 0) {
      return {
        state: "incomplete",
        draft,
        command: null,
        commandQuery,
        valueQuery,
        suggestions: commandMatches,
      };
    }
    return unknownResult(draft, commandQuery, valueQuery);
  }

  const options = optionSets[exactCommand.name] ?? [];
  const suggestions = suggestInlineCommandValues(valueQuery, options);
  if (!valueQuery) {
    return {
      state: "incomplete",
      draft,
      command: exactCommand,
      commandQuery,
      valueQuery,
      suggestions,
    };
  }

  const exactOptions = options.filter((option) => {
    const normalized = normalizeQuery(valueQuery);
    return (
      normalizeQuery(option.value) === normalized ||
      normalizeQuery(option.label) === normalized
    );
  });
  const candidates = exactOptions.length > 0 ? exactOptions : suggestions;

  if (candidates.length === 0) {
    return unknownResult(
      draft,
      commandQuery,
      valueQuery,
      suggestions
    );
  }
  if (candidates.length > 1) {
    return {
      state: "ambiguous",
      draft,
      command: exactCommand,
      commandQuery,
      valueQuery,
      suggestions: candidates,
    };
  }

  const option = candidates[0];
  if (option.disabled) {
    return {
      state: "disabled",
      draft,
      command: exactCommand,
      commandQuery,
      valueQuery,
      option,
      reason: option.disabledReason ?? option.description ?? "Unavailable",
      suggestions: candidates,
    };
  }

  return {
    state: "ready",
    draft,
    command: exactCommand,
    commandQuery,
    valueQuery,
    option,
    suggestions: candidates,
  };
}

export function markInlineCommandExecuted(
  result: Extract<InlineCommandParseResult, { state: "ready" }>
): Extract<InlineCommandParseResult, { state: "executed" }> {
  return {
    ...result,
    state: "executed",
    confirmation: `${result.command.label} set to ${result.option.label}`,
  };
}
