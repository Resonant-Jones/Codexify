export function combineBaseAndPath(base: string | undefined | null, path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (!base) return normalizedPath;

  const trimmedBase = base.replace(/\/+$/, '');
  const hasProtocol = /^[a-z][a-z0-9+.+-]*:\/\//i.test(trimmedBase);

  const baseForUrl = hasProtocol
    ? trimmedBase
    : `http://placeholder${trimmedBase.startsWith('/') ? '' : '/'}${trimmedBase}`;

  const combined = new URL(normalizedPath, `${baseForUrl}/`);

  if (hasProtocol) {
    return combined.toString();
  }

  return combined.pathname + combined.search + combined.hash;
}
