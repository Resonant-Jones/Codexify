import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceNoteSaveModal from "../components/WorkspaceNoteSaveModal";
import { NOTES_LAST_FORMAT_KEY, rememberNoteFormat, suggestNoteTitle } from "../noteSave";

describe("WorkspaceNoteSaveModal", () => {
  beforeEach(() => localStorage.clear());

  it("suggests the first heading, falls back to text, and caps the title", () => {
    expect(suggestNoteTitle("intro\n##  Guardian   Delegation\nrest")).toBe("Guardian Delegation");
    expect(suggestNoteTitle("\n first   meaningful line")).toBe("first meaningful line");
    expect(suggestNoteTitle(" ")).toBe("Untitled Note");
    expect(suggestNoteTitle("x".repeat(100))).toHaveLength(80);
  });

  it("defaults to Markdown, normalizes typed extensions, and allows format changes", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<WorkspaceNoteSaveModal content="# Guardian" onClose={vi.fn()} onSave={onSave} />);
    const title = screen.getByRole("textbox", { name: "Title" });
    const format = screen.getByRole("combobox", { name: "File type" });
    expect(title).toHaveFocus();
    expect(format).toHaveValue("md");
    await user.clear(title);
    await user.type(title, "Guardian Delegation Notes.txt");
    expect(format).toHaveValue("txt");
    await user.selectOptions(format, "md");
    expect(title).toHaveValue("Guardian Delegation Notes");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith("Guardian Delegation Notes", "md");
  });

  it("uses only the last successful format preference and rejects deferred suffixes", async () => {
    rememberNoteFormat("txt");
    expect(localStorage.getItem(NOTES_LAST_FORMAT_KEY)).toBe("txt");
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<WorkspaceNoteSaveModal content="body" onClose={vi.fn()} onSave={onSave} />);
    expect(screen.getByRole("combobox", { name: "File type" })).toHaveValue("txt");
    const title = screen.getByRole("textbox", { name: "Title" });
    await user.clear(title);
    await user.type(title, "planned.pdf");
    expect(screen.getByRole("alert")).toHaveTextContent(".pdf Notes export is not available yet.");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("traps focus and closes on Escape without saving", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onSave = vi.fn();
    render(<WorkspaceNoteSaveModal content="body" onClose={onClose} onSave={onSave} />);
    const title = screen.getByRole("textbox", { name: "Title" });
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(screen.getByRole("button", { name: "Save" })).toHaveFocus();
    await user.tab();
    expect(title).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
    expect(onSave).not.toHaveBeenCalled();
  });
});
