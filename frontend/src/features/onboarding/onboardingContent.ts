import type { SupportedProfileRouteLabel } from "@/contracts/supportedProfileRoutes";
export type TipEntry = {
  id: string;
  category: string;
  title: string;
  summary: string;
  body: string;
  surface: "shared" | "desktop" | "mobile";
  requiredCapability?: SupportedProfileRouteLabel;
};
export const CONTENT_VERSION = 1;
export const TIPS: TipEntry[] = [
  {
    id: "welcome",
    category: "Getting Started",
    title: "An optional introduction",
    summary: "Use Codexify immediately. Skip and resume whenever you like.",
    body: "This introduction explains concepts without moving you around the live interface. Codexify brings different product surfaces around one shared underlying system. Help & Learning in Settings lets you restart setup or open Tips at any time.",
    surface: "shared",
  },
  {
    id: "identity",
    category: "Privacy & Identity",
    title: "Your identity, your choice",
    summary: "Account, profile, username, and display name have different jobs.",
    body: "Your account is private authentication and ownership identity. Your durable social profile identifies you in People. A username is an optional discovery alias; a display name is presentation only. Email is account information, not a social handle, and is not exposed through People discovery. A username need not be your legal name. Participation must not require self-doxxing. Username changes do not break existing relationships or Conversations. This does not promise anonymity.",
    surface: "shared",
  },
  {
    id: "username",
    category: "People",
    title: "Choose a username",
    summary: "Optional discovery on this node, when private-preview messaging is enabled.",
    body: "Usernames use 3–32 lowercase ASCII letters, digits, underscores, or hyphens. First and last characters must be alphanumeric. Reserved system names are unavailable. Uniqueness is scoped to the current node. Numbers are optional; usernames are never derived from email.",
    surface: "shared",
    requiredCapability: "direct_messages",
  },
  {
    id: "desktop-navigation",
    category: "Getting Started",
    title: "Desktop navigation",
    summary: "Guardian, Documents, Gallery, Dashboard, and Settings.",
    body: "Threads and Projects live in the workspace/sidebar model. People is a separate launcher. Open the workspace sidebar for related work and durable conversations.",
    surface: "desktop",
  },
  {
    id: "mobile-navigation",
    category: "Getting Started",
    title: "Phone navigation",
    summary: "Guardian, Documents, and Gallery are primary destinations.",
    body: "Dashboard and Settings are secondary destinations. Access your workspace, Threads, and Projects through the mobile drawer.",
    surface: "mobile",
  },
  {
    id: "guardian",
    category: "Guardian",
    title: "Talk with Guardian",
    summary: "A conversation in your Thread and Project context.",
    body: "Guardian is the conversation surface for working inside a Thread/Project context. Execution capabilities depend on the current runtime and permissions.",
    surface: "shared",
  },
  {
    id: "projects",
    category: "Projects & Threads",
    title: "Organize related work",
    summary: "Projects group work; Threads hold durable conversations.",
    body: "Projects organize related work. Threads are durable conversations within or across relevant project scope according to the workspace's current behavior.",
    surface: "shared",
  },
  {
    id: "documents",
    category: "Documents",
    title: "Keep materials together",
    summary: "Documents is your document and material surface.",
    body: "Use Documents for the materials exposed by your current workspace. Availability and processing depend on the current runtime.",
    surface: "shared",
  },
  {
    id: "gallery",
    category: "Gallery",
    title: "Explore images and media",
    summary: "Gallery shows image and media content exposed by the app.",
    body: "Gallery is the image/media surface. Generation tools depend on the runtime's available capabilities.",
    surface: "shared",
  },
  {
    id: "dashboard",
    category: "Getting Started",
    title: "Start from Dashboard",
    summary: "A high-level workspace and starting surface.",
    body: "Dashboard provides a high-level view and starting point for workspace activity.",
    surface: "shared",
  },
  {
    id: "people",
    category: "People",
    title: "Guardian chat ≠ People messaging",
    summary: "People is human-to-human communication in Private Preview.",
    body: "When enabled, People provides same-node human-to-human Conversations. It is separate from Guardian chat. Cross-node delivery, federation, Rooms, and realtime delivery are not established by this introduction.",
    surface: "shared",
    requiredCapability: "direct_messages",
  },
  {
    id: "settings",
    category: "Settings",
    title: "Make Codexify comfortable",
    summary: "User-facing configuration and Help & Learning.",
    body: "Settings provides user-facing configuration. Help & Learning opens Tips, restarts the introduction or your current device tour, and saves your contextual tips preference.",
    surface: "shared",
  },
];
export const navigationTip = (mobile: boolean) =>
  TIPS.find((tip) => tip.id === (mobile ? "mobile-navigation" : "desktop-navigation"))!;
