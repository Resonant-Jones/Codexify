import * as React from "react";
import { Input } from "@/components/ui/input";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreateProject: (data: { name: string; icon?: string; color?: string }) => Promise<void> | void;
  isSaving?: boolean;
  defaultIcon?: string;
  error?: string | null;
};

export default function CreateProjectModal({
  open,
  onClose,
  onCreateProject,
  isSaving = false,
  defaultIcon = "📁",
  error = null,
}: Props) {
  const [name, setName] = React.useState("");
  const [icon, setIcon] = React.useState(defaultIcon);

  React.useEffect(() => {
    if (!open) {
      setName("");
      setIcon(defaultIcon);
    }
  }, [open, defaultIcon]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    await onCreateProject({ name: trimmed, icon: icon || defaultIcon });
  };

  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-[999] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <form
        onSubmit={handleSubmit}
        className="relative z-[1000] w-[min(520px,90vw)] rounded-2xl border p-5 shadow-2xl"
        style={{
          background: "var(--panel-sheet, var(--panel-bg, #1f1f1f))",
          borderColor: "var(--panel-border)",
        }}
      >
        <div className="mb-4">
          <h3 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
            Create Project
          </h3>
        </div>
        {error && (
          <div
            role="alert"
            className="mb-3 rounded-lg border px-3 py-2 text-sm"
            style={{ borderColor: "rgba(248,113,113,0.6)", color: "#f87171" }}
          >
            {error}
          </div>
        )}
        <div className="space-y-3">
          <div>
            <label className="block text-sm mb-1 opacity-80" htmlFor="projName">
              Name
            </label>
            <Input
              id="projName"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Research, Life Admin…"
              className="rounded-xl"
              style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm mb-1 opacity-80" htmlFor="projIcon">
              Icon (emoji or short label)
            </label>
            <Input
              id="projIcon"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              placeholder={defaultIcon}
              className="rounded-xl"
              style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }}
            />
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="embedded-btn" onClick={onClose} disabled={isSaving}>
            Cancel
          </button>
          <button type="submit" className="embedded-btn" disabled={isSaving || !name.trim()}>
            {isSaving ? "Creating…" : "Create Project"}
          </button>
        </div>
      </form>
    </div>
  );
}
