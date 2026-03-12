export type CompletionDepthMode =
  | "shallow"
  | "normal"
  | "deep"
  | "diagnostic";

export type OperatorTaskTerminalEventType =
  | "task.completed"
  | "task.failed"
  | "task.cancelled"
  | "completion.error";

export type OperatorInspectionStatus =
  | "returned"
  | "not-returned"
  | "not-exposed";

export type OperatorTraceKind = "semantic" | "memory" | "context";

export type OperatorRunInput = {
  userMessage: string;
  threadId?: number | null;
  provider?: string | null;
  model?: string | null;
  depthMode: CompletionDepthMode;
};

export type OperatorProgressUpdate = {
  stage: "posting-message" | "starting-completion" | "waiting-task" | "collecting-results";
  message: string;
};

export type OperatorCompletionStart = {
  taskId: string | null;
  turnId: string | null;
  traceUrl: string | null;
  depthMode: string | null;
  requestedDepthMode: string | null;
  effectiveDepthMode: string | null;
  depthDowngradeReason: string | null;
};

export type OperatorTaskTerminalEvent = {
  type: OperatorTaskTerminalEventType;
  payload: Record<string, unknown> | null;
};

export type OperatorRunResult = {
  threadId: number;
  createdThread: boolean;
  completion: OperatorCompletionStart;
  taskTerminal: OperatorTaskTerminalEvent | null;
  taskWaitTimedOut: boolean;
  taskEventError: string | null;
  messages: Record<string, unknown>[];
  messagesError: string | null;
  trace: Record<string, unknown> | null;
  traceError: string | null;
};

export type OperatorTraceRow = {
  id: string;
  kind: OperatorTraceKind;
  label: string;
  source: string | null;
  rank: number | null;
  score: number | null;
  included: boolean | null;
  preview: string | null;
};

export type OperatorTraceSection = {
  key: OperatorTraceKind;
  title: string;
  rows: OperatorTraceRow[];
};

export type OperatorTraceSummary = {
  status: "idle" | "returned" | "empty" | "unavailable";
  message: string;
  sections: OperatorTraceSection[];
  meta: Array<{ label: string; value: string }>;
};

export type OperatorInspectionField = {
  label: string;
  value: string | null;
  status: OperatorInspectionStatus;
};

export type OperatorPromptAnswerSummary = {
  answerText: string | null;
  answerStatus: OperatorInspectionStatus;
  answerNote: string;
  systemSummary: OperatorInspectionField;
  runtimeFields: OperatorInspectionField[];
  timingFields: OperatorInspectionField[];
  usageFields: OperatorInspectionField[];
  notes: string[];
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function normalizeString(value: unknown): string | null {
  if (typeof value !== "string") {
    if (typeof value === "number" && Number.isFinite(value)) {
      return String(value);
    }
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeNumber(value: unknown): number | null {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "true") return true;
    if (normalized === "false") return false;
  }
  return null;
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    const normalized = normalizeString(value);
    if (normalized) return normalized;
  }
  return null;
}

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    const normalized = normalizeNumber(value);
    if (normalized != null) return normalized;
  }
  return null;
}

function firstBoolean(...values: unknown[]): boolean | null {
  for (const value of values) {
    const normalized = normalizeBoolean(value);
    if (normalized != null) return normalized;
  }
  return null;
}

function hasAnyKey(
  records: Array<Record<string, unknown> | null>,
  keys: string[]
): boolean {
  return records.some((record) =>
    Boolean(record) && keys.some((key) => key in (record as Record<string, unknown>))
  );
}

function shorten(value: string | null, maxLength = 220): string | null {
  if (!value) return null;
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1).trimEnd()}…`;
}

function getMessageRecord(message: Record<string, unknown>): Record<string, unknown> {
  const nested = asRecord(message.message);
  return nested ?? message;
}

function getMessageMetadata(message: Record<string, unknown>): Record<string, unknown> | null {
  const base = getMessageRecord(message);
  return (
    asRecord(base.metadata) ??
    asRecord(base.extra_meta) ??
    asRecord(base.extraMeta) ??
    null
  );
}

function getMessageTurnId(message: Record<string, unknown>): string | null {
  const base = getMessageRecord(message);
  return firstString(base.turn_id, base.turnId, getMessageMetadata(message)?.turn_id);
}

function getMessageId(message: Record<string, unknown>): number | null {
  const base = getMessageRecord(message);
  return firstNumber(base.id, base.message_id, base.messageId);
}

function getAssistantMessage(result: OperatorRunResult): Record<string, unknown> | null {
  const terminalPayload = result.taskTerminal?.payload ?? null;
  const terminalMessageId = firstNumber(terminalPayload?.message_id);
  if (terminalMessageId != null) {
    const byId = result.messages.find((message) => getMessageId(message) === terminalMessageId);
    if (byId) return byId;
  }

  const turnId = result.completion.turnId;
  if (turnId) {
    const byTurn = result.messages.find((message) => {
      const base = getMessageRecord(message);
      return (
        firstString(base.role)?.toLowerCase() === "assistant" &&
        getMessageTurnId(message) === turnId
      );
    });
    if (byTurn) return byTurn;
  }

  const assistants = result.messages.filter((message) => {
    const base = getMessageRecord(message);
    return firstString(base.role)?.toLowerCase() === "assistant";
  });
  return assistants.length > 0 ? assistants[assistants.length - 1] : null;
}

function formatFieldValue(
  label: string,
  value: string | number | boolean | null
): string | null {
  if (value == null) return null;
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return null;
    if (label.toLowerCase().includes("cost")) {
      return `$${value.toFixed(4)}`;
    }
    if (label.toLowerCase().includes("duration")) {
      return `${Math.round(value).toLocaleString()} ms`;
    }
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  return value;
}

function buildField(
  label: string,
  rawValue: string | number | boolean | null,
  status: OperatorInspectionStatus
): OperatorInspectionField {
  return {
    label,
    value: formatFieldValue(label, rawValue),
    status,
  };
}

function toTraceRow(
  kind: OperatorTraceKind,
  raw: unknown,
  index: number
): OperatorTraceRow | null {
  const record = asRecord(raw);
  if (!record) return null;
  const label =
    firstString(record.title, record.label, record.name, record.id, record.node_id) ??
    `Hit ${index + 1}`;
  const preview = shorten(
    firstString(
      record.snippet,
      record.excerpt,
      record.preview,
      record.text,
      record.content,
      record.summary,
      record.message
    )
  );
  const provenance = asRecord(record.provenance);
  const source = firstString(
    record.source,
    record.origin,
    record.path,
    record.namespace,
    record.kind,
    provenance?.relation
  );
  const rank =
    firstNumber(record.rank, record.position, record.order, record.index) ?? index + 1;
  const score = firstNumber(record.score, record.similarity, record.relevance_score);
  const included = firstBoolean(
    record.included,
    record.included_in_prompt,
    record.used,
    record.selected,
    record.accepted
  );

  return {
    id: firstString(record.id, record.node_id, `${kind}-${index + 1}`) ?? `${kind}-${index + 1}`,
    kind,
    label,
    source,
    rank,
    score,
    included,
    preview,
  };
}

export function normalizeTracePayload(trace: unknown): OperatorTraceSummary {
  const record = asRecord(trace);
  if (!record) {
    return {
      status: "unavailable",
      message: "Trace data not returned by current API.",
      sections: [],
      meta: [],
    };
  }

  const semanticRows = asArray(
    record.semantic_hits ?? record.semanticHits ?? record.semantic ?? record.documents
  )
    .map((entry, index) => toTraceRow("semantic", entry, index))
    .filter((entry): entry is OperatorTraceRow => Boolean(entry));

  const memoryRows = asArray(
    record.memory_hits ?? record.memoryHits ?? record.memory ?? record.graph
  )
    .map((entry, index) => toTraceRow("memory", entry, index))
    .filter((entry): entry is OperatorTraceRow => Boolean(entry));

  const contextRows = asArray(
    record.message_context ??
      record.messageContext ??
      record.context_snippets ??
      record.context ??
      record.messages
  )
    .map((entry, index) => toTraceRow("context", entry, index))
    .filter((entry): entry is OperatorTraceRow => Boolean(entry));

  const sections: OperatorTraceSection[] = [
    { key: "semantic", title: "Semantic Hits", rows: semanticRows },
    { key: "memory", title: "Memory Hits", rows: memoryRows },
    { key: "context", title: "Message / Context Snippets", rows: contextRows },
  ];

  const meta = [
    { label: "Active profile", value: firstString(record.active_profile_id) },
    { label: "Provider override", value: firstString(record.provider_override) },
    { label: "Model override", value: firstString(record.model_override) },
    { label: "Retrieval mode", value: firstString(record.retrieval_mode) },
    { label: "Model mode", value: firstString(record.model_mode) },
    { label: "Injection hash", value: firstString(record.injection_hash) },
  ].filter((entry): entry is { label: string; value: string } => Boolean(entry.value));

  const totalRows = sections.reduce((sum, section) => sum + section.rows.length, 0);
  const hasSupportedShape =
    hasAnyKey([record], [
      "documents",
      "graph",
      "semantic_hits",
      "semanticHits",
      "memory_hits",
      "memoryHits",
      "messages",
      "context",
      "message_context",
      "messageContext",
      "context_snippets",
    ]) || meta.length > 0;

  if (totalRows > 0) {
    return {
      status: "returned",
      message: "Trace data returned by the current API.",
      sections,
      meta,
    };
  }

  if (hasSupportedShape) {
    return {
      status: "empty",
      message: "Current API returned no trace hits for this run.",
      sections,
      meta,
    };
  }

  return {
    status: "unavailable",
    message: "Trace data not returned by current API.",
    sections,
    meta,
  };
}

export function buildPromptAnswerSummary(
  result: OperatorRunResult | null
): OperatorPromptAnswerSummary {
  if (!result) {
    return {
      answerText: null,
      answerStatus: "not-returned",
      answerNote: "Run a completion to inspect the final answer.",
      systemSummary: buildField(
        "System / Context Summary",
        null,
        "not-exposed"
      ),
      runtimeFields: [],
      timingFields: [],
      usageFields: [],
      notes: [],
    };
  }

  const terminalPayload = result.taskTerminal?.payload ?? null;
  const assistantMessage = getAssistantMessage(result);
  const assistantBase = assistantMessage ? getMessageRecord(assistantMessage) : null;
  const assistantMetadata = assistantMessage ? getMessageMetadata(assistantMessage) : null;
  const trace = result.trace;
  const traceRecord = asRecord(trace);

  const answerText = firstString(assistantBase?.content);
  let answerNote = "Final answer loaded from the persisted assistant message.";
  let answerStatus: OperatorInspectionStatus = answerText ? "returned" : "not-returned";

  if (!answerText) {
    answerNote =
      firstString(terminalPayload?.error, result.messagesError, result.taskEventError) ??
      "No assistant answer was returned for this run.";
  }

  if (result.taskTerminal?.type === "task.failed" || result.taskTerminal?.type === "completion.error") {
    answerStatus = answerText ? "returned" : "not-returned";
    answerNote =
      firstString(terminalPayload?.error, result.taskEventError) ??
      "The completion task failed before an answer was persisted.";
  }

  if (result.taskTerminal?.type === "task.cancelled") {
    answerStatus = answerText ? "returned" : "not-returned";
    answerNote = answerText
      ? "The task was cancelled after an answer was already persisted."
      : "The completion task was cancelled before an answer was persisted.";
  }

  const systemSummaryKeys = [
    "system_summary",
    "systemSummary",
    "context_summary",
    "contextSummary",
    "prompt_summary",
    "promptSummary",
  ];
  const systemSummaryValue = firstString(
    terminalPayload?.system_summary,
    terminalPayload?.context_summary,
    traceRecord?.system_summary,
    traceRecord?.context_summary,
    assistantMetadata?.system_summary,
    assistantMetadata?.context_summary
  );
  const systemSummaryStatus: OperatorInspectionStatus = systemSummaryValue
    ? "returned"
    : hasAnyKey([terminalPayload, traceRecord, assistantMetadata], systemSummaryKeys)
      ? "not-returned"
      : "not-exposed";

  const usageRecord =
    asRecord(terminalPayload?.usage) ??
    asRecord(assistantMetadata?.usage) ??
    asRecord(traceRecord?.usage);
  const usageShapePresent =
    Boolean(usageRecord) ||
    hasAnyKey([terminalPayload, assistantMetadata, traceRecord], [
      "prompt_tokens",
      "input_tokens",
      "completion_tokens",
      "output_tokens",
      "total_tokens",
      "cost_usd",
      "estimated_cost_usd",
    ]);

  const promptTokens = firstNumber(
    usageRecord?.prompt_tokens,
    usageRecord?.input_tokens,
    terminalPayload?.prompt_tokens,
    terminalPayload?.input_tokens,
    assistantMetadata?.prompt_tokens,
    assistantMetadata?.input_tokens
  );
  const completionTokens = firstNumber(
    usageRecord?.completion_tokens,
    usageRecord?.output_tokens,
    terminalPayload?.completion_tokens,
    terminalPayload?.output_tokens,
    assistantMetadata?.completion_tokens,
    assistantMetadata?.output_tokens
  );
  const totalTokens = firstNumber(
    usageRecord?.total_tokens,
    terminalPayload?.total_tokens,
    assistantMetadata?.total_tokens
  );
  const costUsd = firstNumber(
    usageRecord?.cost_usd,
    usageRecord?.estimated_cost_usd,
    terminalPayload?.cost_usd,
    terminalPayload?.estimated_cost_usd,
    assistantMetadata?.cost_usd,
    assistantMetadata?.estimated_cost_usd
  );

  const durationMs = firstNumber(
    terminalPayload?.duration_ms,
    assistantMetadata?.duration_ms,
    assistantMetadata?.latency_ms
  );
  const durationStatus: OperatorInspectionStatus = durationMs != null
    ? "returned"
    : result.taskTerminal || result.taskWaitTimedOut || result.taskEventError
      ? "not-returned"
      : "not-exposed";

  const providerUsed = firstString(terminalPayload?.provider);
  const modelUsed = firstString(terminalPayload?.model);
  const providerModelStatus: OperatorInspectionStatus = result.taskTerminal
    ? "not-returned"
    : result.taskWaitTimedOut || result.taskEventError
      ? "not-returned"
      : "not-exposed";

  const runtimeFields: OperatorInspectionField[] = [
    buildField("Thread ID", result.threadId, "returned"),
    buildField("Task ID", result.completion.taskId, result.completion.taskId ? "returned" : "not-returned"),
    buildField("Turn ID", result.completion.turnId, result.completion.turnId ? "returned" : "not-returned"),
    buildField("Provider Used", providerUsed, providerUsed ? "returned" : providerModelStatus),
    buildField("Model Used", modelUsed, modelUsed ? "returned" : providerModelStatus),
    buildField(
      "Requested Depth",
      result.completion.requestedDepthMode ?? result.completion.depthMode,
      result.completion.requestedDepthMode || result.completion.depthMode ? "returned" : "not-returned"
    ),
    buildField(
      "Effective Depth",
      result.completion.effectiveDepthMode ?? result.completion.depthMode,
      result.completion.effectiveDepthMode || result.completion.depthMode ? "returned" : "not-returned"
    ),
    buildField(
      "Depth Downgrade Reason",
      result.completion.depthDowngradeReason ?? "none",
      "returned"
    ),
  ];

  const timingFields: OperatorInspectionField[] = [
    buildField("Duration", durationMs, durationStatus),
  ];

  const usageStatus: OperatorInspectionStatus = usageShapePresent
    ? "not-returned"
    : "not-exposed";
  const usageFields: OperatorInspectionField[] = [
    buildField("Prompt Tokens", promptTokens, promptTokens != null ? "returned" : usageStatus),
    buildField(
      "Completion Tokens",
      completionTokens,
      completionTokens != null ? "returned" : usageStatus
    ),
    buildField("Total Tokens", totalTokens, totalTokens != null ? "returned" : usageStatus),
    buildField("Estimated Cost", costUsd, costUsd != null ? "returned" : usageStatus),
  ];

  const notes = [
    result.taskWaitTimedOut
      ? "Task terminal event was not observed before the operator timeout; diagnostics may be partial."
      : null,
    result.taskEventError ? `Task event stream: ${result.taskEventError}` : null,
    result.messagesError ? `Messages endpoint: ${result.messagesError}` : null,
    result.traceError ? `Trace endpoint: ${result.traceError}` : null,
  ].filter((note): note is string => Boolean(note));

  return {
    answerText,
    answerStatus,
    answerNote,
    systemSummary: buildField(
      "System / Context Summary",
      systemSummaryValue,
      systemSummaryStatus
    ),
    runtimeFields,
    timingFields,
    usageFields,
    notes,
  };
}
