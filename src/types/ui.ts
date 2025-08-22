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
};

export type ExtColors = Record<string, string>;

export type GalleryItem = { src: string; prompt: string };

