const lastLoggedAtByKey = new Map<string, number>();

/**
 * Execute a logging callback at most once per TTL window for a given key.
 */
export function logOnce(key: string, ttlMs: number, fn: () => void): void {
  const now = Date.now();
  const lastLoggedAt = lastLoggedAtByKey.get(key) ?? 0;
  if (ttlMs <= 0 || now - lastLoggedAt > ttlMs) {
    lastLoggedAtByKey.set(key, now);
    fn();
  }
}

export default logOnce;
