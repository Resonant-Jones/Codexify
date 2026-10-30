/**
 * ConversationMinimap - narrow left-edge rail that projects the loaded
 * transcript into navigable sections.
 *
 * Interaction contract:
 * - the rail is stationary while the transcript scrolls
 * - hovering or focusing a mark opens a bounded, non-modal preview
 * - previewing never scrolls the transcript and never fetches messages
 * - clicking a pointer-selected destination commits the jump
 * - on touch-capable input a tap opens the preview and a separate
 *   "Go to turn" action commits the navigation
 */
import { ArrowLeft } from "lucide-react";
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type {
  ConversationNavigationEntry,
  ConversationSection,
} from "@/features/chat/conversationNavigation";
import { resolveConversationEntrySections } from "@/features/chat/conversationNavigation";
import { cn } from "@/lib/utils";

import styles from "./ConversationMinimap.module.css";

const PREVIEW_CLOSE_DELAY_MS = 220;

export type ConversationMinimapProps = {
  sections: ConversationSection[];
  entries: ConversationNavigationEntry[];
  activeSectionId: string | null;
  /** True when the supplied history still has older messages to load. */
  hasMore: boolean;
  /** Identifies the current thread so stale previews can be dismissed. */
  threadId: number;
  canGoBack: boolean;
  onJump: (sectionId: string) => boolean;
  onBack: () => boolean;
};

export function ConversationMinimap({
  sections,
  entries,
  activeSectionId,
  hasMore,
  threadId,
  canGoBack,
  onJump,
  onBack,
}: ConversationMinimapProps) {
  const [previewEntryId, setPreviewEntryId] = useState<string | null>(null);
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pointerTypeRef = useRef<string>("mouse");
  const markRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const sectionsById = useMemo(() => {
    const map = new Map<string, ConversationSection>();
    for (const section of sections) map.set(section.id, section);
    return map;
  }, [sections]);

  const previewEntry = useMemo(
    () => entries.find((entry) => entry.id === previewEntryId) ?? null,
    [entries, previewEntryId]
  );

  const previewSections = useMemo(
    () =>
      previewEntry
        ? resolveConversationEntrySections(previewEntry, sectionsById)
        : [],
    [previewEntry, sectionsById]
  );

  const clearCloseTimer = useCallback(() => {
    if (closeTimerRef.current !== null) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);

  const scheduleClose = useCallback(() => {
    if (closeTimerRef.current !== null) return;
    closeTimerRef.current = setTimeout(() => {
      closeTimerRef.current = null;
      setPreviewEntryId(null);
      setSelectedSectionId(null);
    }, PREVIEW_CLOSE_DELAY_MS);
  }, []);

  const closePreview = useCallback(() => {
    clearCloseTimer();
    setPreviewEntryId(null);
    setSelectedSectionId(null);
  }, [clearCloseTimer]);

  const openPreview = useCallback(
    (entry: ConversationNavigationEntry) => {
      clearCloseTimer();
      setPreviewEntryId(entry.id);
      setSelectedSectionId(entry.sectionIds[0] ?? null);
    },
    [clearCloseTimer]
  );

  // A thread switch must never leave the previous thread's preview visible.
  useEffect(() => {
    closePreview();
  }, [closePreview, threadId]);

  // An outside interaction dismisses the preview.
  useEffect(() => {
    if (!previewEntry) return;
    if (typeof document === "undefined") return;

    const handlePointerDown = (event: Event) => {
      const target = event.target as Node | null;
      const root = rootRef.current;
      if (root && target && root.contains(target)) return;
      closePreview();
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, [closePreview, previewEntry]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current !== null) {
        clearTimeout(closeTimerRef.current);
        closeTimerRef.current = null;
      }
    };
  }, []);

  const rootRef = useRef<HTMLDivElement | null>(null);

  const isTouchInteraction = useCallback(() => {
    return pointerTypeRef.current === "touch";
  }, []);

  const commitJump = useCallback(
    (sectionId: string) => {
      const jumped = onJump(sectionId);
      if (jumped) closePreview();
      return jumped;
    },
    [closePreview, onJump]
  );

  const handleMarkActivate = useCallback(
    (entry: ConversationNavigationEntry) => {
      // A range entry cannot resolve to one destination, so it always opens
      // the preview and lets the reader choose the exact turn.
      if (entry.kind === "range") {
        openPreview(entry);
        return;
      }

      const sectionId = entry.sectionIds[0];
      if (!sectionId) return;

      if (isTouchInteraction()) {
        // Touch opens the preview. A separate "Go to turn" action commits.
        openPreview(entry);
        return;
      }

      commitJump(sectionId);
    },
    [commitJump, isTouchInteraction, openPreview]
  );

  const handleDestinationActivate = useCallback(
    (sectionId: string) => {
      setSelectedSectionId(sectionId);
      if (isTouchInteraction()) return;
      commitJump(sectionId);
    },
    [commitJump, isTouchInteraction]
  );

  const handleGoToTurn = useCallback(() => {
    if (!selectedSectionId) return;
    commitJump(selectedSectionId);
  }, [commitJump, selectedSectionId]);

  const handleRailKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        closePreview();
        return;
      }

      if (event.key === "ArrowDown" || event.key === "ArrowRight") {
        event.preventDefault();
        const next = markRefs.current[index + 1];
        if (next) next.focus();
        return;
      }

      if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
        event.preventDefault();
        const previous = markRefs.current[index - 1];
        if (previous) previous.focus();
        return;
      }

      if (event.key === "Home") {
        event.preventDefault();
        const first = markRefs.current[0];
        if (first) first.focus();
        return;
      }

      if (event.key === "End") {
        event.preventDefault();
        const last = markRefs.current[markRefs.current.length - 1];
        if (last) last.focus();
      }
    },
    [closePreview]
  );

  const previewSectionsById = useMemo(() => {
    const map = new Map<string, ConversationSection>();
    for (const section of previewSections) map.set(section.id, section);
    return map;
  }, [previewSections]);

  if (entries.length === 0) return null;

  const markCount = entries.length;

  return (
    <div
      ref={rootRef}
      className={styles.root}
      data-testid="conversation-minimap"
      data-thread-id={threadId}
    >
      <nav
        className={styles.rail}
        aria-label="Conversation navigation"
        onMouseEnter={clearCloseTimer}
        onMouseLeave={scheduleClose}
        onFocus={clearCloseTimer}
      >
        <div className={styles.marks}>
          {entries.map((entry, index) => {
            const position = markCount === 1 ? 50 : (index / (markCount - 1)) * 100;
            const isActive =
              activeSectionId !== null && entry.sectionIds.includes(activeSectionId);
            const isPreviewed = previewEntryId === entry.id;
            const entrySections = resolveConversationEntrySections(
              entry,
              sectionsById
            );
            const activeLabel = entrySections.find(
              (section) => section.id === activeSectionId
            );

            return (
              <button
                key={entry.id}
                ref={(node) => {
                  markRefs.current[index] = node;
                }}
                type="button"
                className={styles.markSlot}
                style={{
                  top: `${position}%`,
                  height: `${100 / markCount}%`,
                }}
                data-testid="conversation-minimap-mark"
                data-entry-kind={entry.kind}
                data-section-ids={entry.sectionIds.join(",")}
                data-active={isActive ? "true" : "false"}
                data-previewed={isPreviewed ? "true" : "false"}
                aria-label={
                  activeLabel
                    ? `${entry.label}, currently reading`
                    : entry.label
                }
                aria-expanded={isPreviewed}
                onPointerDown={(event) => {
                  pointerTypeRef.current = event.pointerType || "mouse";
                }}
                onMouseEnter={() => openPreview(entry)}
                onFocus={() => openPreview(entry)}
                onClick={() => handleMarkActivate(entry)}
                onKeyDown={(event) => handleRailKeyDown(event, index)}
              >
                <span
                  className={cn(
                    styles.mark,
                    isActive && styles.markActive,
                    isPreviewed && styles.markPreviewed
                  )}
                  aria-hidden="true"
                />
              </button>
            );
          })}
        </div>

        {canGoBack ? (
          <button
            type="button"
            className={styles.backButton}
            data-testid="conversation-minimap-back"
            aria-label="Back to previous position"
            title="Back to previous position"
            onClick={() => {
              onBack();
            }}
          >
            <ArrowLeft className="h-3 w-3" aria-hidden="true" />
          </button>
        ) : null}
      </nav>

      {previewEntry ? (
        <div
          className={styles.preview}
          role="dialog"
          aria-modal="false"
          aria-label="Conversation preview"
          data-testid="conversation-minimap-preview"
          onMouseEnter={clearCloseTimer}
          onMouseLeave={scheduleClose}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.stopPropagation();
              closePreview();
            }
          }}
        >
          <div className={styles.previewHeader}>
            <span className={styles.previewTitle}>{previewEntry.label}</span>
            {hasMore ? (
              <span
                className={styles.previewNote}
                data-testid="conversation-minimap-loaded-note"
              >
                Loaded history
              </span>
            ) : null}
          </div>

          <ul className={styles.previewList}>
            {previewEntry.sectionIds.map((sectionId) => {
              const section = previewSectionsById.get(sectionId);
              if (!section) return null;
              const turnNumber = previewEntry.startIndex + 1 +
                previewEntry.sectionIds.indexOf(sectionId);
              return (
                <li key={sectionId}>
                  <button
                    type="button"
                    className={styles.previewItem}
                    data-testid="conversation-minimap-destination"
                    data-section-id={sectionId}
                    data-selected={selectedSectionId === sectionId ? "true" : "false"}
                    data-active={activeSectionId === sectionId ? "true" : "false"}
                    onPointerDown={(event) => {
                      pointerTypeRef.current = event.pointerType || "mouse";
                    }}
                    onMouseEnter={() => setSelectedSectionId(sectionId)}
                    onFocus={() => setSelectedSectionId(sectionId)}
                    onClick={() => handleDestinationActivate(sectionId)}
                  >
                    <span className={styles.previewItemTitle}>
                      Turn {turnNumber}
                    </span>
                    <span className={styles.previewItemText}>
                      {section.preview || "(no text)"}
                    </span>
                    {section.replyPreview ? (
                      <span
                        className={styles.previewItemReply}
                        data-testid="conversation-minimap-reply"
                      >
                        {section.replyPreview}
                      </span>
                    ) : null}
                    {section.attachmentLabels.length > 0 ? (
                      <span className={styles.previewItemAttachments}>
                        {section.attachmentLabels.join(", ")}
                      </span>
                    ) : null}
                  </button>
                </li>
              );
            })}
          </ul>

          <div className={styles.previewActions}>
            <button
              type="button"
              className={styles.goToTurn}
              data-testid="conversation-minimap-go-to-turn"
              disabled={!selectedSectionId}
              onClick={handleGoToTurn}
            >
              Go to turn
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default ConversationMinimap;
