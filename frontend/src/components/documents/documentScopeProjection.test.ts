import { describe, expect, it } from "vitest";

import {
  getDocumentScopeQuery,
  getDocumentUploadScope,
  seedDocumentsScope,
  selectDocumentsProject,
  selectDocumentsThread,
  type GuardianSidebarSnapshot,
} from "./documentScopeProjection";

const snapshot: GuardianSidebarSnapshot = {
  threads: [
    {
      id: "11",
      title: "Guardian thread",
      lastMessage: "Sidebar preview only",
      unread: 0,
      participants: [],
      projectId: "7",
      projectName: "Project A",
    },
  ],
  activeThreadId: 11,
  selectedProjectId: 7,
  selectedProjectName: "Project A",
  activeThreadProjectId: 7,
};

describe("document scope projection", () => {
  it("seeds thread scope from an active Guardian thread", () => {
    expect(seedDocumentsScope(snapshot, 9)).toEqual({
      kind: "thread",
      projectId: 7,
      threadId: 11,
    });
  });

  it("seeds project scope when Guardian has no active thread", () => {
    expect(
      seedDocumentsScope({ ...snapshot, activeThreadId: null, activeThreadProjectId: null }, 9)
    ).toEqual({ kind: "project", projectId: 7, threadId: null });
  });

  it("clears the selected thread when Documents selects a project", () => {
    expect(selectDocumentsProject(9)).toEqual({
      kind: "project",
      projectId: 9,
      threadId: null,
    });
  });

  it("derives a selected thread project from the loaded directory", () => {
    expect(selectDocumentsThread("11", snapshot.threads)).toEqual({
      kind: "thread",
      projectId: 7,
      threadId: 11,
    });
  });

  it("uses exactly one API scope parameter", () => {
    expect(
      getDocumentScopeQuery({ kind: "thread", projectId: 7, threadId: 11 })
    ).toEqual({ limit: 100, thread_id: 11 });
    expect(
      getDocumentScopeQuery({ kind: "project", projectId: 7, threadId: null })
    ).toEqual({ limit: 100, project_id: 7 });
  });

  it("keeps upload project and thread values aligned with the selected scope", () => {
    expect(
      getDocumentUploadScope({ kind: "thread", projectId: 7, threadId: 11 })
    ).toEqual({ projectId: 7, threadId: 11 });
    expect(
      getDocumentUploadScope({ kind: "project", projectId: 7, threadId: null })
    ).toEqual({ projectId: 7, threadId: null });
  });
});
