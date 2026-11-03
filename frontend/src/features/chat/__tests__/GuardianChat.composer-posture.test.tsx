import { render, screen } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import GuardianChat from "@/features/chat/GuardianChat";
import { SHELL_BREAKPOINTS } from "@/components/persona/layout/shellBreakpointContract";
import { getMobileShellProfile } from "@/components/persona/layout/mobileShellProfile";
import api from "@/lib/api";

/**
 * MOB-G3-TASK-1 — dedicated composer posture regression test.
 *
 * The landing prompt-first unit used to carry `transform: translateY(-50%)`,
 * a value calibrated for a `position: fixed` layout that commit 93bb09a37
 * replaced with flow positioning inside a flex stage that already centers its
 * child. The leftover transform lifted the whole unit — composer included —
 * by half its own height, so the new-thread composer floated high.
 *
 * The active composer also ignored the canonical shell safe-area inset that
 * the sibling jump-to-latest overlay already consumes.
 *
 * This file pins both, on desktop and on a phone-class viewport.
 */

// jsdom's CSS parser rejects `env(...)`, so the safe-area token cannot be
// asserted through the style property. The wiring is asserted with a
// parseable sentinel, and the real token is asserted against the profile
// contract itself.
const profileState = vi.hoisted(() => ({
  active: false,
  bottomSafeArea: "0px",
}));

vi.mock("@/components/persona/layout/mobileShellProfile", async (importOriginal) => {
  const actual =
    await importOriginal<
      typeof import("@/components/persona/layout/mobileShellProfile")
    >();
  return {
    ...actual,
    useMobileShellProfile: () => {
      const profile = actual.getMobileShellProfile({
        viewportClass: profileState.active ? "phone" : "desktop",
      });
      return {
        ...profile,
        active: profileState.active,
        chat: {
          ...profile.chat,
          composer: {
            ...profile.chat.composer,
            bottomSafeArea: profileState.bottomSafeArea,
          },
        },
      };
    },
  };
});

vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  buildLlmCatalogPath: () => "/llm/catalog",
  buildChatThreadsPath: () => "/api/chat/threads",
  buildChatCompletePath: (threadId: string | number) => `/chat/${threadId}/complete`,
  clearInFlightCompletionTurnId: vi.fn(),
  getInFlightCompletionTurnId: vi.fn(() => null),
  getBackendOutageRemainingMs: vi.fn(() => 0),
  hasRequestAuthCredential: vi.fn(() => true),
}));

vi.mock("@/lib/authState", () => ({
  useAuthState: () => ({
    ready: true,
    status: "authenticated",
    token: "test-token",
  }),
  getAuthState: () => ({
    ready: true,
    status: "authenticated",
    token: "test-token",
  }),
  checkAuthGate: () => true,
  requireAuthReady: () => true,
}));

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: any) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children, asChild, ...props }: any) => {
    if (asChild) return children;
    return (
      <button type="button" {...props}>
        {children}
      </button>
    );
  },
  DropdownMenuContent: ({ children }: any) => <div>{children}</div>,
  DropdownMenuItem: ({ children, onClick, ...props }: any) => (
    <button type="button" onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

vi.mock("@/features/guardian/components/Composer", () => ({
  Composer: ({
    onSend,
    presentationMode,
  }: {
    onSend?: (text: string) => Promise<void>;
    presentationMode?: "landing" | "conversation";
  }) => (
    <div data-testid="composer-stub" data-presentation-mode={presentationMode}>
      <textarea data-testid="composer-textarea" placeholder="Write a message…" />
      <button
        type="button"
        data-testid="composer-send"
        onClick={() => void onSend?.("First prompt")}
      >
        Send
      </button>
    </div>
  ),
}));

vi.mock("@/features/chat/ChatView", () => ({
  default: () => <div data-testid="chat-view-stub" />,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("@/features/chat/useChat", () => {
  const snapshot = {
    messages: [],
    loading: false,
    error: null,
    hasMore: false,
    activateThread: vi.fn(),
    refreshSnapshot: vi.fn().mockResolvedValue([]),
    loadOlderMessages: vi.fn().mockResolvedValue([]),
    completionState: {
      isCompleting: false,
      activeTaskId: null,
      activeThreadId: null,
      startedAt: null,
    },
    startCompletion: vi.fn(),
    endCompletion: vi.fn(),
  };
  return {
    useChat: () => snapshot,
    default: () => snapshot,
  };
});

const originalInnerWidth = window.innerWidth;

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
}

type GuardianChatProps = Parameters<typeof GuardianChat>[0];

// A non-numeric active thread id means no persisted thread is open, which is
// the landing (prompt-first) presentation.
const LANDING_THREAD = { id: "draft", title: "Draft" } as any;
const ACTIVE_THREAD = { id: "42", title: "Active" } as any;

function renderChat(props: Partial<GuardianChatProps> = {}) {
  return render(
    <GuardianChat
      guardianName="Guardian"
      userName="tester"
      onSendMessage={vi.fn().mockResolvedValue(undefined)}
      activeThread={LANDING_THREAD}
      {...props}
    />
  );
}

describe("composer posture", () => {
  beforeEach(() => {
    setViewportWidth(SHELL_BREAKPOINTS.desktop);
    profileState.active = false;
    profileState.bottomSafeArea = "0px";
  });

  afterEach(() => {
    setViewportWidth(originalInnerWidth);
    vi.clearAllMocks();
  });

  describe("canonical shell profile contract", () => {
    it("declares the phone safe-area inset and a zero desktop inset", () => {
      const phone = getMobileShellProfile({ viewportClass: "phone" });
      const desktop = getMobileShellProfile({ viewportClass: "desktop" });

      expect(phone.chat.composer.bottomSafeArea).toBe(
        "env(safe-area-inset-bottom, 0px)"
      );
      expect(desktop.chat.composer.bottomSafeArea).toBe("0px");
    });
  });

  describe("landing posture", () => {
    it("centers the prompt-first unit in the stage without a vertical transform", () => {
      renderChat();

      const stage = screen.getByTestId("guardian-landing-stage");
      const unit = screen.getByTestId("guardian-landing-unit");

      // The stage owns the centering.
      expect(stage.className).toContain("items-center");
      expect(stage.className).toContain("justify-center");

      // The unit carries no vertical transform of its own.
      expect(unit.style.transform).toBe("");
      expect(unit.getAttribute("style") ?? "").not.toContain("translateY");
    });

    it("keeps the landing unit in normal document flow", () => {
      renderChat();

      const unit = screen.getByTestId("guardian-landing-unit");

      // Preserved contract from 93bb09a37: the unit is not fixed-positioned.
      expect(unit.style.position).not.toBe("fixed");
      expect(unit.style.left).toBe("");
      expect(unit.style.right).toBe("");
    });

    it("does not apply a bottom safe-area inset to the centered landing composer", () => {
      setViewportWidth(390);
      renderChat();

      const positioner = screen.getByTestId("composer-shell-positioner");

      // The landing composer is centered, so the viewport's bottom inset does
      // not apply to it.
      expect(positioner.style.paddingBottom).toBe("");
    });
  });

  describe("active-thread posture", () => {
    it("applies the canonical shell safe-area inset on a phone", () => {
      profileState.active = true;
      profileState.bottomSafeArea = "11px";
      renderChat({ activeThread: ACTIVE_THREAD });

      const positioner = screen.getByTestId("composer-shell-positioner");

      // The composer positioner consumes the canonical profile inset.
      expect(positioner.style.paddingBottom).toBe("11px");
    });

    it("keeps the desktop composer inset inert", () => {
      profileState.active = false;
      profileState.bottomSafeArea = "0px";
      renderChat({ activeThread: ACTIVE_THREAD });

      const positioner = screen.getByTestId("composer-shell-positioner");

      // The desktop profile declares a zero inset, so desktop geometry is
      // unchanged.
      expect(positioner.style.paddingBottom).toBe("0px");
    });

    it("never positions the active composer as a fixed overlay", () => {
      renderChat({ activeThread: ACTIVE_THREAD });

      const positioner = screen.getByTestId("composer-shell-positioner");
      const shell = screen.getByTestId("composer-shell");

      expect(positioner.style.position).not.toBe("fixed");
      expect(shell.style.position).not.toBe("fixed");
    });

    it("preserves the composer instance across the landing and conversation postures", () => {
      const view = renderChat();

      const landingComposer = screen.getByTestId("composer-stub");
      expect(landingComposer).toHaveAttribute("data-presentation-mode", "landing");

      view.rerender(
        <GuardianChat
          guardianName="Guardian"
          userName="tester"
          onSendMessage={vi.fn().mockResolvedValue(undefined)}
          activeThread={ACTIVE_THREAD}
        />
      );

      const conversationComposer = screen.getByTestId("composer-stub");
      expect(conversationComposer).toHaveAttribute(
        "data-presentation-mode",
        "conversation"
      );

      // The same DOM node is reused, so draft, focus, and attachments are
      // never reset by the posture change.
      expect(conversationComposer).toBe(landingComposer);
    });
  });
});
