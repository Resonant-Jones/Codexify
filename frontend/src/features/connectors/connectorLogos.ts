import githubLogo from '@/assets/connectors/github.svg';

const CONNECTOR_LOGOS: Record<string, string> = {
  github: githubLogo,
};

export function getConnectorLogo(type?: string, id?: string): string | undefined {
  const key = (type || id || '').toLowerCase();
  return CONNECTOR_LOGOS[key];
}

/**
 * Logo lookup for canonical Connections catalog entries. Falls back to the
 * shared connector logo map; entries without a committed asset render a
 * monogram instead (see `getConnectionMonogram`).
 */
export function getConnectionLogo(id?: string): string | undefined {
  return getConnectorLogo(id, id);
}

/** Monogram fallback for catalog entries without a committed logo asset. */
export function getConnectionMonogram(id?: string): string {
  const seed = (id || '').trim();
  return (seed.charAt(0) || '?').toUpperCase();
}
