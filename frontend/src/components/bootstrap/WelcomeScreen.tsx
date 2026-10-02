import { Button } from "@/components/ui/button";
import SystemSurface from "@/components/system-surface/SystemSurface";

type WelcomeScreenProps = {
  onEnter: () => void;
};

export default function WelcomeScreen({ onEnter }: WelcomeScreenProps) {
  return (
    <div
      className="codexify-system-surface-screen min-h-screen"
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-screen-title"
    >
      <div className="codexify-system-surface-screen__dialog max-w-2xl">
        <SystemSurface
          actions={
            <>
              <Button
                type="button"
                variant="system"
                onClick={onEnter}
              >
                Enter Codexify
              </Button>
              <p className="codexify-system-surface-screen__action-note text-sm leading-6">
                The workspace unlocks after this step.
              </p>
            </>
          }
          category="SETUP"
          details={
            <div className="codexify-system-surface-screen__detail-grid grid grid-cols-1 gap-[var(--shell-gap)] sm:grid-cols-3">
              <section className="codexify-system-surface-screen__detail">
                <h2 className="codexify-system-surface-screen__detail-title text-xs font-bold leading-normal tracking-wider">
                  Local first
                </h2>
                <p className="codexify-system-surface-screen__detail-copy text-sm leading-6">
                  Startup stays anchored to the local repo, runtime files, and
                  health surfaces instead of a separate desktop-only bootstrap.
                </p>
              </section>
              <section className="codexify-system-surface-screen__detail">
                <h2 className="codexify-system-surface-screen__detail-title text-xs font-bold leading-normal tracking-wider">
                  Explicit gating
                </h2>
                <p className="codexify-system-surface-screen__detail-copy text-sm leading-6">
                  Guardian, Dashboard, Documents, and Gallery stay locked until
                  the real runtime proves it is ready.
                </p>
              </section>
              <section className="codexify-system-surface-screen__detail">
                <h2 className="codexify-system-surface-screen__detail-title text-xs font-bold leading-normal tracking-wider">
                  One time
                </h2>
                <p className="codexify-system-surface-screen__detail-copy text-sm leading-6">
                  This welcome screen is dismissed per local profile so repeat
                  launches can go straight to the workspace once the local beta
                  loop is green.
                </p>
              </section>
            </div>
          }
          description={
            <>
              The backend process is reachable, startup has completed, Redis
              and chat health are green, and the local beta readiness contract
              is satisfied. Enter when you want the full workspace surface to
              become interactive.
            </>
          }
          headingLevel="h1"
          statusLabel="Ready"
          title="Codexify is ready."
          titleId="welcome-screen-title"
          tone="success"
        />
      </div>
    </div>
  );
}
