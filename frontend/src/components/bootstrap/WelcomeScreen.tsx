import { Button } from "@/components/ui/button";

type WelcomeScreenProps = {
  onEnter: () => void;
};

export default function WelcomeScreen({ onEnter }: WelcomeScreenProps) {
  return (
    <div
      className="flex h-full w-full items-center justify-center p-6 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-screen-title"
    >
      <div className="absolute inset-0 bg-black/35 backdrop-blur-xl" />
      <div
        className="relative z-10 w-full max-w-2xl overflow-hidden rounded-[26px] border shadow-2xl"
        style={{
          borderColor: "var(--panel-border-strong, var(--panel-border))",
          background:
            "linear-gradient(155deg, rgba(12,18,30,0.95), rgba(19,29,42,0.86))",
          color: "var(--text)",
          boxShadow: "0 32px 110px rgba(0,0,0,0.34)",
        }}
      >
        <div className="border-b px-6 py-4 sm:px-8" style={{ borderColor: "var(--panel-border)" }}>
          <span
            className="inline-flex items-center rounded-full border px-3 py-1 text-xs uppercase tracking-[0.24em]"
            style={{
              borderColor: "var(--chip-border)",
              background: "rgba(255,255,255,0.04)",
              color: "var(--muted)",
            }}
          >
            Welcome
          </span>
        </div>

        <div className="space-y-6 px-6 py-7 sm:px-8 sm:py-9">
          <div className="space-y-3">
            <h1
              id="welcome-screen-title"
              className="text-2xl font-semibold tracking-[-0.02em] sm:text-3xl"
            >
              Codexify is ready.
            </h1>
            <p className="max-w-xl text-sm leading-6 sm:text-[15px]" style={{ color: "var(--muted)" }}>
              The local shell is up, the runtime gate has passed, and the workspace will stay yours to shape.
              Enter when you want the full surface to become interactive.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div
              className="rounded-[18px] border px-4 py-4"
              style={{
                borderColor: "var(--panel-border)",
                background: "rgba(255,255,255,0.04)",
              }}
            >
              <div className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                Local first
              </div>
              <p className="mt-2 text-sm leading-6" style={{ color: "var(--text)" }}>
                The native shell opens before the rest of the runtime is asked to do any work.
              </p>
            </div>
            <div
              className="rounded-[18px] border px-4 py-4"
              style={{
                borderColor: "var(--panel-border)",
                background: "rgba(255,255,255,0.04)",
              }}
            >
              <div className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                Permissioned
              </div>
              <p className="mt-2 text-sm leading-6" style={{ color: "var(--text)" }}>
                Runtime checks stay explicit, machine-readable, and easy to retry when the environment changes.
              </p>
            </div>
            <div
              className="rounded-[18px] border px-4 py-4"
              style={{
                borderColor: "var(--panel-border)",
                background: "rgba(255,255,255,0.04)",
              }}
            >
              <div className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
                One time
              </div>
              <p className="mt-2 text-sm leading-6" style={{ color: "var(--text)" }}>
                This welcome screen only appears once per local profile unless you clear its stored dismissal.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" className="rounded-full px-5" onClick={onEnter}>
              Enter Codexify
            </Button>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              The workspace unlocks after this step.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
