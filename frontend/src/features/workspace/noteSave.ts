export const NOTE_FORMATS = [
  { value: "md", label: "Markdown", extension: ".md" },
  { value: "txt", label: "Plain Text", extension: ".txt" },
] as const;

export type NoteFormat = (typeof NOTE_FORMATS)[number]["value"];
export const NOTES_LAST_FORMAT_KEY = "cfy.workspace.notes.last-format.v1";
const DEFERRED_EXTENSIONS = new Set(["pdf", "doc", "docx", "png", "jpeg", "codex"]);

export function readLastNoteFormat(): NoteFormat {
  try {
    const value = window.localStorage.getItem(NOTES_LAST_FORMAT_KEY);
    return NOTE_FORMATS.find((entry) => entry.value === value)?.value ?? "md";
  } catch {
    return "md";
  }
}

export function rememberNoteFormat(format: NoteFormat): void {
  try {
    window.localStorage.setItem(NOTES_LAST_FORMAT_KEY, format);
  } catch {
    // Preference storage is best effort; document persistence is server-owned.
  }
}

export function suggestNoteTitle(content: string): string {
  const lines = content.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const heading = lines.find((line) => /^#{1,6}\s+\S/.test(line));
  const candidate = heading ? heading.replace(/^#{1,6}\s+/, "") : lines[0] ?? "Untitled Note";
  return candidate.replace(/\s+/g, " ").trim().slice(0, 80) || "Untitled Note";
}

export function resolveNoteTitle(rawTitle: string, selectedFormat: NoteFormat): {
  title: string;
  format: NoteFormat;
  filename: string;
  error: string | null;
} {
  let title = rawTitle.replace(/\s+/g, " ").trim();
  const suffix = title.match(/\.([^.\s]+)$/)?.[1]?.toLowerCase();
  if (suffix && DEFERRED_EXTENSIONS.has(suffix)) {
    return { title, format: selectedFormat, filename: "", error: `.${suffix} Notes export is not available yet.` };
  }
  const format = NOTE_FORMATS.find((entry) => entry.value === suffix)?.value ?? selectedFormat;
  if (suffix === "md" || suffix === "txt") title = title.slice(0, -(suffix.length + 1)).trim();
  if (!title) return { title, format, filename: "", error: "Enter a title." };
  return { title, format, filename: `${title}.${format}`, error: null };
}
