import { X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import DirectMessageInbox from "@/components/direct-messages/DirectMessageInbox";
import type { RuntimeRouteCapabilityState } from "@/contracts/supportedProfileRoutes";


import ContactCard from "./ContactCard";
import ContactsList from "./ContactsList";
import type { ContactListItem } from "./types";
import type { PeopleMessagingState } from "./usePeopleMessagingState";
import "./ContactsWindow.css";

type ContactsWindowProps = {
  state: PeopleMessagingState;
  contacts: ContactListItem[];
  onRequestCreate?: () => void;
  capabilityState: RuntimeRouteCapabilityState;
  sourceThreadId: number | null;
};

export default function ContactsWindow({
  state,
  contacts,
  onRequestCreate,
  capabilityState,
  sourceThreadId,
}: ContactsWindowProps) {
  const [selectedContactId, setSelectedContactId] = useState<string | null>(null);
  const selectedContact = useMemo(
    () => contacts.find((contact) => contact.id === selectedContactId) ?? null,
    [contacts, selectedContactId]
  );

  const open = state.peopleOpen;
  const onClose = state.closePeople;

  useEffect(() => {
    if (!open || typeof window === "undefined") return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open]);

  if (!open || typeof document === "undefined") return null;

  const portalTarget =
    document.getElementById("cfy-portal-root") ??
    document.getElementById("app") ??
    document.getElementById("root") ??
    document.body ??
    document.documentElement;

  const inboxContent = (
    <DirectMessageInbox
      capabilityState={capabilityState}
      sourceThreadId={sourceThreadId}
      state={state}
    />
  );

  return createPortal(
    <div className="contacts-window-overlay" role="presentation">
      <div
        className="contacts-window-window"
        role="dialog"
        aria-modal="true"
        aria-label="People"
        data-testid="contacts-window"
        onClick={(event) => event.stopPropagation()}
        onPointerDown={(event) => event.stopPropagation()}
      >
        <header className="contacts-window-header">
          <div>
            <h2 className="contacts-window-title">People</h2>
            <p className="contacts-window-subcopy">Private communication space</p>
          </div>
          <div className="contacts-window-header-actions">
            <button type="button" className="contacts-window-close" aria-label="Close People" onClick={onClose}>
              <X size={17} aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="people-tabs" role="tablist" aria-label="People sections">
          <button
            type="button"
            role="tab"
            aria-selected={state.activeTab === "inbox"}
            className={`people-tab ${state.activeTab === "inbox" ? "is-active" : ""}`}
            onClick={() => state.setTab("inbox")}
          >
            Inbox
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={state.activeTab === "contacts"}
            className={`people-tab ${state.activeTab === "contacts" ? "is-active" : ""}`}
            onClick={() => state.setTab("contacts")}
          >
            Contacts
          </button>
        </div>

        {state.activeTab === "contacts" ? (
          contacts.length === 0 ? (
            <section className="contacts-window-empty" aria-label="Empty contact list">
              <div className="contacts-window-empty-mark" aria-hidden="true">◎</div>
              <p className="contacts-window-eyebrow">Private home container</p>
              <h3>No contacts yet</h3>
              <p>
                This is the private home container for people you may collaborate with later.
                Contacts do not grant access or expose presence.
              </p>
              {onRequestCreate ? (
                <button type="button" className="contacts-window-primary-action" onClick={onRequestCreate}>
                  New Contact
                </button>
              ) : null}
            </section>
          ) : (
            <div className="contacts-window-body">
              <ContactsList
                contacts={contacts}
                selectedId={selectedContactId}
                onSelect={(contact) => setSelectedContactId(contact.id)}
              />
              <ContactCard contact={selectedContact} />
            </div>
          )
        ) : (
          <div className="people-inbox-body">{inboxContent}</div>
        )}
      </div>
    </div>,
    portalTarget
  );
}
