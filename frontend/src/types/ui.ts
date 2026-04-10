import type { ChatExecution } from "@/types/chat";

export type ThemeMode = "light" | "dark" | "system";

export type MessageAttachment = {
  id: string;
  kind: "image" | "document";
  src?: string;
  name?: string;
};

export type Message = {
  id: string;
  authorId: string;
  authorName: string;
  content: string;
  createdAt: number | null;
  status?: "sending" | "sent" | "delivered" | "read";
  attachments?: MessageAttachment[];
  execution?: ChatExecution;
};

export type ProfileMode = "local" | "cloud";

export type ThreadConfig = {
  providerId: string;
  modelId: string;
  inferenceMode: string;
  retrievalSource: string;
  personaId: string | null;
};

export type Thread = {
  id: string;
  title: string;
  lastMessage: string;
  unread: number;
  participants: Array<{ id: string; name: string }>;
  messages: Message[];
  projectId?: string | null;
  projectName?: string | null;
  lastInteractionAt?: string | null;
  parentId?: string | null;
  archivedAt?: string | null;
  metadata?: Record<string, unknown> | null;
  activeProfileId?: string | null;
  profileName?: string | null;
  profileMode?: ProfileMode | null;
  providerOverride?: string | null;
  modelOverride?: string | null;
  threadConfig?: ThreadConfig | null;
};

export type ExtColors = {
  pdf: string;
  doc: string;
  md: string;
  png: string;
  sketch: string;
  txt: string;
  docx: string;
  jpeg: string;
  codex: string;
};

export type GalleryItem = { src: string; prompt: string; mock?: boolean };
