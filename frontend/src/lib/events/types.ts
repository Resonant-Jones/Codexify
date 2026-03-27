export type LiveEventEntity =
  | "task"
  | "agent_run"
  | "message"
  | "approval"
  | "command_run"
  | "thread"
  | "connector"
  | "system";

export type LiveEvent = {
  id: string | null;
  type: string;
  entity: LiveEventEntity;
  entity_id: string;
  thread_id: string | null;
  status?: string;
  payload?: unknown;
  data?: unknown;
  raw?: unknown;
  ts: number;
};
