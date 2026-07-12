import { useEffect, useMemo, useState } from "react";

import type { ContactListItem } from "./types";

type ContactFilter = "all" | "favorites" | "archived" | "blocked";

type ContactsListProps = {
  contacts: ContactListItem[];
  selectedId: string | null;
  onSelect: (contact: ContactListItem) => void;
};

const FILTERS: Array<{ id: ContactFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "favorites", label: "Favorites" },
  { id: "archived", label: "Archived" },
  { id: "blocked", label: "Blocked" },
];

function getInitials(displayName: string): string {
  const initials = displayName
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
  return initials || "?";
}

function matchesSearch(contact: ContactListItem, query: string): boolean {
  if (!query) return true;
  const searchable = [
    contact.displayName,
    contact.localAlias,
    contact.preferredContactMethod,
    ...(contact.externalHandles ?? []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return searchable.includes(query);
}

export default function ContactsList({
  contacts,
  selectedId,
  onSelect,
}: ContactsListProps) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ContactFilter>("all");

  const visibleContacts = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return contacts.filter((contact) => {
      const matchesFilter =
        filter === "all" ||
        (filter === "favorites" && contact.favorite) ||
        (filter === "archived" && contact.archived) ||
        (filter === "blocked" && contact.blocked);
      return matchesFilter && matchesSearch(contact, normalizedQuery);
    });
  }, [contacts, filter, query]);

  useEffect(() => {
    const selectedContact = visibleContacts.find((contact) => contact.id === selectedId);
    if (selectedContact) return;
    const firstVisibleContact = visibleContacts[0];
    if (firstVisibleContact) onSelect(firstVisibleContact);
  }, [onSelect, selectedId, visibleContacts]);

  return (
    <section className="contacts-window-list" aria-label="Contact list">
      <div className="contacts-window-list-toolbar">
        <label className="contacts-window-search-label" htmlFor="contacts-search">
          Search contacts
        </label>
        <input
          id="contacts-search"
          className="contacts-window-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by name or handle"
        />
        <div className="contacts-window-filters" aria-label="Contact filters">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`contacts-window-filter ${filter === item.id ? "is-active" : ""}`}
              aria-pressed={filter === item.id}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="contacts-window-list-items" role="list">
        {visibleContacts.length === 0 ? (
          <p className="contacts-window-list-empty">No contacts match this view.</p>
        ) : (
          visibleContacts.map((contact) => (
            <button
              key={contact.id}
              type="button"
              className={`contacts-window-list-row ${selectedId === contact.id ? "is-selected" : ""}`}
              aria-selected={selectedId === contact.id}
              onClick={() => onSelect(contact)}
            >
              <span className="contacts-window-avatar" aria-hidden="true">
                {getInitials(contact.displayName)}
              </span>
              <span className="contacts-window-row-copy">
                <span className="contacts-window-row-name">{contact.displayName}</span>
                {contact.localAlias ? (
                  <span className="contacts-window-row-alias">{contact.localAlias}</span>
                ) : null}
                {contact.preferredContactMethod ? (
                  <span className="contacts-window-row-method">
                    {contact.preferredContactMethod}
                  </span>
                ) : null}
                <span className="contacts-window-statuses">
                  {contact.favorite ? <span className="contacts-window-chip">Favorite</span> : null}
                  {contact.archived ? <span className="contacts-window-chip">Archived</span> : null}
                  {contact.blocked ? <span className="contacts-window-chip">Blocked</span> : null}
                </span>
              </span>
            </button>
          ))
        )}
      </div>
    </section>
  );
}
