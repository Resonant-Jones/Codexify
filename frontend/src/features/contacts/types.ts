/**
 * Presentational frontend shape only; this is not the canonical persistence schema.
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
