import React from "react";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", () => ({ default: mocks }));
vi.mock("@/features/chat/components/generativeUi/GenerativeUIRenderer", () => ({ default: () => <div data-testid="widget-runtime" /> }));
import { SavedWidgetLibrary, SaveWidgetControls } from "./SavedWidgets";
afterEach(cleanup);
beforeEach(() => { mocks.get.mockReset(); mocks.post.mockReset(); });
const widget = { widget_id: "sw_test", name: "Calculator", current_revision: 2 };
const artifact = { version: 1, kind: "sandbox", html: "<button>Go</button>", js: "document.body.onclick=()=>{}" };
it("lists metadata without starting code, launches a pinned revision and destroys it on dismissal", async () => {
  mocks.get.mockImplementation((url: string) => Promise.resolve({ data: url.endsWith("/revisions/2")
    ? { widget_id: widget.widget_id, revision: 2, artifact_snapshot: artifact }
    : url.endsWith("/sw_test") ? { source_withheld: false, revisions: [{revision:1},{revision:2}] }
    : { widgets: [widget], count: 1, next_offset: null } }));
  render(<SavedWidgetLibrary />);
  fireEvent.click(await screen.findByText("Calculator · Version 2"));
  expect(screen.queryByTestId("widget-runtime")).toBeNull();
  fireEvent.click(screen.getByText("Launch widget"));
  await screen.findByTestId("widget-runtime");
  expect(mocks.get).toHaveBeenCalledWith("/api/saved-widgets/sw_test/revisions/2");
  fireEvent.click(screen.getByText("Close widget"));
  expect(screen.queryByTestId("widget-runtime")).toBeNull();
});
it("sends original marker coordinates, never client artifact source", async () => {
  mocks.get.mockResolvedValue({ data: { widgets: [], count: 0, next_offset: null } });
  mocks.post.mockResolvedValue({ data: { revision: 1 } });
  const content = "<!-- cfy-ui:broken -->" + "<!-- cfy-ui:" + encodeURIComponent(JSON.stringify(artifact)) + " -->";
  render(<SaveWidgetControls content={content} threadId={12} messageId="34" />);
  fireEvent.click(screen.getByText("Save widget to Library"));
  fireEvent.click(await screen.findByText("Save as new"));
  await waitFor(() => expect(mocks.post).toHaveBeenCalledWith("/api/saved-widgets",
    { thread_id: 12, message_id: 34, artifact_index: 1, name: "My widget" }));
});
it("appends against the selected base revision only after an explicit save", async () => {
  mocks.get.mockResolvedValue({data:{widgets:[widget],count:1,next_offset:null}});
  mocks.post.mockResolvedValue({data:{revision:3}});
  const content = "<!-- cfy-ui:" + encodeURIComponent(JSON.stringify(artifact)) + " -->";
  render(<SaveWidgetControls content={content} threadId={12} messageId="34" />);
  fireEvent.click(screen.getByText("Save widget to Library"));
  await screen.findByText("Calculator — new version after 2");
  expect(mocks.post).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole("combobox"), {target:{value:"sw_test"}});
  fireEvent.click(screen.getByText("Save new version"));
  await waitFor(() => expect(mocks.post).toHaveBeenCalledWith("/api/saved-widgets/sw_test/revisions",
    {thread_id:12,message_id:34,artifact_index:0,base_revision:2}));
});

it("keeps inaccessible resources unavailable instead of launching", async () => {
  mocks.get.mockImplementation((url: string) => url.endsWith("/sw_test")
    ? Promise.resolve({data:{source_withheld:true}})
    : Promise.resolve({data:{widgets:[widget],count:1,next_offset:null}}));
  render(<SavedWidgetLibrary />);
  fireEvent.click(await screen.findByText("Calculator · Version 2"));
  await screen.findByRole("alert");
  expect(screen.queryByTestId("widget-runtime")).toBeNull();
});

