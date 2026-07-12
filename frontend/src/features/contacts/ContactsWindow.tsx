import { X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import ContactCard from "./ContactCard";
import ContactsList from "./ContactsList";
import type { ContactListItem } from "./types";
import "./ContactsWindow.css";

type ContactsWindowProps = {
  open: boolean;
  onClose: () => void;
  contacts: ContactListItem[];
  onRequestCreate?: () => void;
};

export default function ContactsWindow({
  open,
  onClose,
  contacts,
  onRequestCreate,
}: ContactsWindowProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedContact = useMemo(
    () => contacts.find((contact) => contact.id === selectedId) ?? null,
    [contacts, selectedId]
  );
  const handleSelect = useCallback((contact: ContactListItem) => {
    setSelectedId(contact.id);
  }, []);

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

  return createPortal(
    <div className="contacts-window-overlay" role="presentation">
      <div
        className="contacts-window-window"
        role="dialog"
        aria-modal="true"
        aria-label="Contacts"
        data-testid="contacts-window"
        onClick={(event) => event.stopPropagation()}
        onPointerDown={(event) => event.stopPropagation()}
      >
        <header className="contacts-window-header">
          <div>
            <h2 className="contacts-window-title">Contacts</h2>
            <p className="contacts-window-subcopy">Private contact list</p>
          </div>
          <div className="contacts-window-header-actions">
            <span className="contacts-window-count">
              {contacts.length} {contacts.length === 1 ? "contact" : "contacts"}
            </span>
            <button type="button" className="contacts-window-close" aria-label="Close Contacts" onClick={onClose}>
              <X size={17} aria-hidden="true" />
            </button>
          </div>
        </header>

        {contacts.length === 0 ? (
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
            <ContactsList contacts={contacts} selectedId={selectedId} onSelect={handleSelect} />
            <ContactCard contact={selectedContact} />
          </div>
        )}
      </div>
    </div>,
    portalTarget
  );
}
