
Codex prompt — Project defaults + Threads/Projects UX sweep

You are editing a Vite + React + TS app with Tailwind and shadcn/ui. Follow all guardrails exactly.

Guardrails (do not break)
 • Do not touch components/ui/LayeredCard.tsx internals.
 • Composer anchoring is sacred: edge-composer lives bottom-pinned with a 3px internal rim. Do not change structure; styles are scoped via CSS vars.
 • Keep the global 6px page rim, 12px inter-card gap, 3px internal rim.
 • Respect existing light/dark tokens (--panel-bg, --text, --panel-border, --chip-bg, --elevation-shadow-*).
 • No duplicate imports (avoid the “React already declared” and duplicate ProjectContext imports).
 • If you can’t find a referenced file, stop and report which file is missing—don’t guess.

What we’re building
 • “Loose threads” becomes a first-class project (id: "loose").
 • Selection rule: if a project is actively selected, new chats are created in that project. If no project is selected, new chats go to a configurable default project (ships as "loose").
 • Add a Setting: “Default project for new chats” (dropdown). Persist in localStorage key cfy.defaultProjectId. Default value "loose".
 • Treat “Loose threads” as just another project in the Projects tab (no separate “Loose” button). User can switch between Threads and Projects tabs. Searching happens only in Threads.
 • Filter behavior:
 • If selected project is "loose" → show threads with !thread.projectId.
 • If selected is some id → show threads with thread.projectId === id.

Files to touch
 • src/components/layout/AppShell.tsx
 • src/components/chat/Sidebar.tsx  (if present & used; otherwise keep all in AppShell’s GuardianChat)
 • src/components/settings/… (where SettingsView lives; in this repo it’s inside AppShell.tsx as a local component—modify there)
 • src/components/documents/DocumentsView.tsx and src/components/gallery/GalleryView.tsx only if you already consume ProjectContext for filtering (don’t add if not needed)

Implementation steps
 1. Centralize the projects list
 • In AppShell.tsx (top of AppShell()), create:

const projects: Project[] = React.useMemo(
  () => [
    { id: "loose", name: "Loose threads" },
    { id: "p1", name: "Sovereign AI Principles" },
    { id: "p2", name: "Health & Wellness" },
  ],
  []
);

 • Pass projects into GuardianChat and SettingsView as props.
 • Remove any local projects arrays inside GuardianChat/Sidebar to avoid duplication.

 2. Default project state + persistence
 • In AppShell.tsx (top-level state near other localStorage reads):

const [defaultProjectId, setDefaultProjectId] = useState<string>(() =>
  typeof window === "undefined" ? "loose" : localStorage.getItem("cfy.defaultProjectId") || "loose"
);
useEffect(() => {
  if (typeof window !== "undefined") localStorage.setItem("cfy.defaultProjectId", defaultProjectId);
}, [defaultProjectId]);

 • Pass defaultProjectId and setDefaultProjectId to SettingsView.
 • Keep existing ProjectContext (projectId, setProjectId) as-is.

 3. New chat → target project
 • In both places that create a new chat (desktop titlebar button and mobile sheet, if any), route through:

const targetPid = projectId ?? defaultProjectId; // selected project wins; else default
const id = `t_${Date.now()}`;
setThreads(prev => [
  { id, title: "New Chat", lastMessage: "", unread: 0,
    projectId: targetPid === "loose" ? undefined : targetPid,
    participants: [{ id:"me", name:userName }, { id:"bot", name:guardianName }],
    messages: []
  },
  ...prev,
]);
setActiveId(id);

 • Important: we store no projectId field for loose threads (so existing filters !t.projectId keep working).

 4. Threads/Projects header
 • In the Threads panel header UI:
 • Keep two tabs: Threads / Projects (remove any third “Loose” tab/button).
 • In Projects tab list, render Loose threads as the first project item using the LayeredCard chip style (you already have that component/style—reuse).
 • Selecting Loose threads sets setProjectId(null); other projects set setProjectId(project.id); then switch back to Threads tab.
 5. Search placeholder
 • Compute placeholder like:

const placeholder = projectId
  ? `Search threads in ${projects.find(p => p.id === projectId)?.name ?? "Project"}…`
  : `Search threads…`; // when null (loose) or no selection

 • Do not special-case “Loose” in the placeholder; keep it simple.

 6. Filtering logic (unchanged intent, just clean)
 • In your threads list derivation:

const base = projectId
  ? threads.filter(t => t.projectId === projectId)
  : threads.filter(t => !t.projectId); // loose
// Apply query filter atop `base`

 7. Settings: Default project
 • In SettingsView props, add: { projects: Project[], defaultProjectId: string, setDefaultProjectId: (id: string) => void }.
 • Add a small section under the Appearance tab (or wherever you prefer) titled “Projects”:
 • Label: Default project for new chats
 • A Select/Dropdown bound to defaultProjectId with options:
 • { value: "loose", label: "Loose threads" }
 • Each project from projects except "loose".
 • Persist via setDefaultProjectId.
 • Do not add any composer chips/buttons for now.
 8. Design fidelity
 • Keep LayeredCard chip styling for projects/threads rows (3px p-inset, glass bezel, subtle hover lift). Don’t change LayeredCard internals.
 • Maintain the 6px page rim around main areas and the 12px gap between columns.
 • Keep the composer’s 3px internal rim and edge-to-edge behavior.
 9. Migrations
 • No DB—just runtime. Existing loose threads already have !projectId. Leave them as-is. Nothing to backfill.

Acceptance checks (manually verify)
 • Launch app:
 • Default defaultProjectId is “loose” (check localStorage).
 • Projects tab shows Loose threads + other projects as LayeredCard chips.
 • Selecting a project switches to Threads tab and filters list.
 • New Chat while a project is selected → thread carries that projectId.
 • New Chat with no project selected → thread goes to defaultProjectId (loose by default → no projectId on thread).
 • Settings shows Default project for new chats; changing it updates localStorage and affects the next New Chat (when no project selected).
 • Light/Dark styling, rims, and composer anchoring are unchanged.

Notes
 • If Sidebar.tsx also renders the Threads/Projects area, mirror the logic there (or keep it all centralized inside GuardianChat—don’t duplicate state).
 • If you see any duplicate React or ProjectContext imports in a file, remove the duplicates rather than renaming symbols.

Now implement the steps above. When done, print a short summary of:
 • files changed
 • whether new chats route correctly (selected vs default)
 • how to change default in Settings
 • any nontrivial tradeoffs or TODOs

⸻
