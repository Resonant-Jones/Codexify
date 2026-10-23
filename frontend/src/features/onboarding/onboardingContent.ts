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
    body: "This introduction explains things without moving you around the app. You can skip it at any point and pick it up later. Settings → Help & Learning lets you restart this introduction or open Tips whenever you want a reference.",
    surface: "shared",
  },
  {
    id: "identity",
    category: "Privacy & Identity",
    title: "Your identity, your choice",
    summary:
      "Your account, your profile, and your username are separate, and your email is never shown to others.",
    body: "Your account is how you sign in and what you own. Your profile is what other people see. A username is an optional way to be found, and a display name is just how you appear. Your email is never exposed through People, and you never have to use your real name. Changing your username keeps your existing relationships and Conversations intact. This is privacy, not anonymity.",
    surface: "shared",
  },
  {
    id: "username",
    category: "People",
    title: "Choose a username",
    summary: "An optional way to be found on this node, when Private Preview messaging is enabled.",
    body: "Pick 3–32 characters: lowercase letters, numbers, underscores, or hyphens. The first and last characters must be letters or numbers, and some names are reserved. Names are unique on this node. You can skip this entirely, and we never build a username from your email.",
    surface: "shared",
    requiredCapability: "direct_messages",
  },
  {
    id: "desktop-navigation",
    category: "Getting Started",
    title: "Desktop navigation",
    summary: "Guardian, Documents, Gallery, Dashboard, and Settings.",
    body: "Threads and Projects live in the workspace/sidebar, so related work and durable conversations stay together. People opens separately, on its own.",
    surface: "desktop",
  },
  {
    id: "mobile-navigation",
    category: "Getting Started",
    title: "Phone navigation",
    summary: "Guardian, Documents, and Gallery are primary destinations.",
    body: "Access your workspace, Threads, and Projects through the mobile drawer. Dashboard and Settings are secondary destinations.",
    surface: "mobile",
  },
  {
    id: "guardian",
    category: "Guardian",
    title: "Talk with Guardian",
    summary: "A conversation in your Thread and Project context.",
    body: "Guardian is where you talk to your assistant. It works inside a Thread or Project, and what it can do depends on what this device's setup allows.",
    surface: "shared",
  },
  {
    id: "projects",
    category: "Projects & Threads",
    title: "Organize related work",
    summary: "Projects group work; Threads hold durable conversations.",
    body: "Projects group related work. Threads are conversations that stick around, inside a Project or across the ones you work in.",
    surface: "shared",
  },
  {
    id: "documents",
    category: "Documents",
    title: "Keep materials together",
    summary: "Documents is your document and material surface.",
    body: "Documents is where you keep the files and materials your workspace gives you. What you can open and work on depends on this device's setup.",
    surface: "shared",
  },
  {
    id: "gallery",
    category: "Gallery",
    title: "Explore images and media",
    summary: "Gallery shows image and media content exposed by the app.",
    body: "Gallery is where your images and media live. The generation tools it offers depend on what this device's setup provides.",
    surface: "shared",
  },
  {
    id: "dashboard",
    category: "Getting Started",
    title: "Start from Dashboard",
    summary: "A high-level workspace and starting surface.",
    body: "Dashboard gives you a wide view of what is happening in your workspace, and a place to start.",
    surface: "shared",
  },
  {
    id: "people",
    category: "People",
    title: "Guardian chat ≠ People messaging",
    summary: "People is human-to-human communication in Private Preview.",
    body: "People is for talking to other people, separately from Guardian. It is Private Preview and works between people on this node. Chatting across nodes, federation, and Rooms are not part of this introduction.",
    surface: "shared",
    requiredCapability: "direct_messages",
  },
  {
    id: "settings",
    category: "Settings",
    title: "Make Codexify comfortable",
    summary: "Configure how Codexify works, and find Help & Learning.",
    body: "Settings is where you configure how Codexify works. Help & Learning opens Tips, restarts this introduction or the tour for this device, and lets you turn contextual tips on or off.",
    surface: "shared",
  },
];
export const navigationTip = (mobile: boolean) =>
  TIPS.find((tip) => tip.id === (mobile ? "mobile-navigation" : "desktop-navigation"))!;
