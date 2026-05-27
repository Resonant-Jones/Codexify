export type GuardianDelegationTranscriptMetadataKey =
  | "intent_id"
  | "run_id"
  | "thread_id"
  | "source_message_id"
  | "delivery_key"
  | "result_message_id"
  | "approval_state"
  | "approval_source"
  | "approval_mode"
  | "intent_status"
  | "run_status"
  | "visibility_status";

export type GuardianDelegationTranscriptScalar =
  | boolean
  | number
  | string
  | null;

export type GuardianDelegationTranscriptMetadata = Partial<
  Record<
    GuardianDelegationTranscriptMetadataKey,
    GuardianDelegationTranscriptScalar
  >
> &
  Record<string, unknown>;

export type GuardianDelegationSourceThreadReference = {
  thread_id?: number | string | null;
  source_message_id?: number | string | null;
};

export type GuardianDelegationTranscriptItem = {
  item_id: string;
  kind: string;
  source: string;
  created_at: string | null;
  summary: string;
  metadata?: GuardianDelegationTranscriptMetadata | null;
};

export type GuardianDelegationTranscriptResponse = {
  inspection_only: boolean;
  intent_id: string;
  thread_id: number | string | null;
  source_message_id: number | string | null;
  project_id: number | string | null;
  run_id: string | null;
  approval_state: string | null;
  approval_source: string | null;
  approval_mode: string | null;
  intent_status: string | null;
  run_status: string | null;
  visibility_status: string | null;
  result_message_id: number | string | null;
  result_delivered_at: string | null;
  source_thread_reference?: GuardianDelegationSourceThreadReference | null;
  transcript_items?: GuardianDelegationTranscriptItem[];
};
