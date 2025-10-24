export type ThemeMode = "light" | "dark" | "system";

export type Message = {
  id: string;
  authorId: string;
  authorName: string;
  content: string;
  createdAt: number;
  status?: "sending" | "sent" | "delivered" | "read";
};

export type Thread = {
  id: string;
  title: string;
  lastMessage: string;
  unread: number;
  participants: Array<{ id: string; name: string }>;
  messages: Message[];
  projectId?: string | null;
  parentId?: string | null;
  archivedAt?: string | null;
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
};

export type GalleryItem = { src: string; prompt: string; mock?: boolean };
