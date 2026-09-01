/**
 * Presentational frontend shape only; this is not the canonical persistence schema.
 *
 * Direct-messaging shapes live in the canonical client module
 * (`@/lib/direct-messages`); nothing here re-derives backend authority.
 */
export type ContactListItem = {
  id: string;
  displayName: string;
  localAlias?: string;
  relationshipNote?: string;
  preferredContactMethod?: string;
  externalHandles?: string[];
  favorite?: boolean;
  archived?: boolean;
  blocked?: boolean;
  discoveryPathLabel?: string;
  createdAt?: string;
  updatedAt?: string;
};

export type PeopleTab = "inbox" | "contacts";
