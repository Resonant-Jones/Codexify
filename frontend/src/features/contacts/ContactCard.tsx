import type { ContactListItem } from "./types";

type ContactCardProps = {
  contact: ContactListItem | null;
};

function getInitials(displayName: string): string {
  return displayName
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase() || "?";
}

function formatMetadata(value?: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

export default function ContactCard({ contact }: ContactCardProps) {
  if (!contact) {
    return (
      <section className="contacts-window-card contacts-window-card-empty" aria-label="Contact details">
        <p className="contacts-window-eyebrow">Contact card</p>
        <h3>Select a contact</h3>
        <p>Contact details will appear here.</p>
      </section>
    );
  }

  const createdAt = formatMetadata(contact.createdAt);
  const updatedAt = formatMetadata(contact.updatedAt);

  return (
    <section className="contacts-window-card" aria-label={`${contact.displayName} contact card`}>
      <div className="contacts-window-card-identity">
        <span className="contacts-window-avatar contacts-window-avatar-large" aria-hidden="true">
          {getInitials(contact.displayName)}
        </span>
        <div>
          <p className="contacts-window-eyebrow">Contact card</p>
          <h3>{contact.displayName}</h3>
          {contact.localAlias ? <p className="contacts-window-card-alias">{contact.localAlias}</p> : null}
        </div>
      </div>

      <div className="contacts-window-statuses">
        {contact.favorite ? <span className="contacts-window-chip">Favorite</span> : null}
        {contact.archived ? <span className="contacts-window-chip">Archived</span> : null}
        {contact.blocked ? <span className="contacts-window-chip">Blocked</span> : null}
      </div>

      <dl className="contacts-window-details">
        {contact.preferredContactMethod ? (
          <div><dt>Preferred contact method</dt><dd>{contact.preferredContactMethod}</dd></div>
        ) : null}
        {contact.externalHandles?.length ? (
          <div><dt>External handles</dt><dd>{contact.externalHandles.join(", ")}</dd></div>
        ) : null}
        {contact.discoveryPathLabel ? (
          <div><dt>Added through</dt><dd>{contact.discoveryPathLabel}</dd></div>
        ) : null}
        {contact.relationshipNote ? (
          <div><dt>Private note</dt><dd className="contacts-window-private-note">{contact.relationshipNote}</dd></div>
        ) : null}
        {createdAt ? <div><dt>Created</dt><dd>{createdAt}</dd></div> : null}
        {updatedAt ? <div><dt>Updated</dt><dd>{updatedAt}</dd></div> : null}
      </dl>

      <aside className="contacts-window-boundary" aria-label="Private relationship record">
        <strong>Private relationship record</strong>
        <p>
          This card does not prove account ownership, identity verification, permission,
          presence, or Space participation.
        </p>
      </aside>
    </section>
  );
}
