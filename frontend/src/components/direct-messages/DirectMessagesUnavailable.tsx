/**
 * Bounded unavailable state for the direct-messages surface.
 *
 * Rendered when the accepted runtime route capability for
 * `direct_messages` is not `available` — the Inbox fails closed rather
 * than hardcoding a supported profile or inventing capability truth.
 */

export default function DirectMessagesUnavailable() {
  return (
    <main
      className="flex min-h-screen items-center justify-center p-6"
      data-testid="direct-messages-unavailable"
    >
      <section
        aria-labelledby="direct-messages-unavailable-heading"
        className="w-full max-w-md rounded-[var(--radius-tile,19px)] border border-[var(--panel-border)] bg-[var(--panel-bg)]/95 p-8 text-[var(--text)] shadow-2xl backdrop-blur-xl"
      >
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-subtle)]">
          Codexify
        </p>
        <h1
          className="mt-3 text-2xl font-semibold tracking-[-0.03em]"
          id="direct-messages-unavailable-heading"
        >
          Direct messages unavailable
        </h1>
        <p className="mt-3 text-sm leading-6 text-[var(--text-subtle)]">
          This runtime profile does not provide the direct-messaging Inbox.
          Direct messages remain private-profile functionality and have not
          been widened to other postures.
        </p>
      </section>
    </main>
  );
}
