import {
  DEFAULT_COMPOSER_INFERENCE_MODE,
  type ComposerInferenceMode,
} from "@/types/inference";

export type TabId = string;

export interface SessionTab {
  tabId: TabId;
  threadId?: string;
  pendingThread: boolean;
  title?: string;
  providerId?: string | null;
  modelId: string;
  inferenceMode: ComposerInferenceMode;
  createdAt: string;
  updatedAt: string;
}

export interface SessionState {
  deviceId: string;
  userId: string;
  tabs: SessionTab[];
  activeTabId: TabId;
  drafts?: Record<TabId, string>;
  version: number;
  updatedAt: string;
}

// `version` is persisted in Redis payloads to support future schema upgrades.
export const SESSION_SCHEMA_VERSION = 2;

// Open tab/session state can be reconstructed and is safe to expire.
export const SESSION_TTL_SECONDS = 60 * 60 * 24 * 14; // 14 days

// Draft text is sad-to-lose; keep it for a longer window.
export const SESSION_DRAFTS_TTL_SECONDS = 60 * 60 * 24 * 30; // 30 days

export const DEFAULT_MODEL_ID = "default";
export const DEFAULT_PROVIDER_ID: string | null = null;
export const DEFAULT_INFERENCE_MODE = DEFAULT_COMPOSER_INFERENCE_MODE;
