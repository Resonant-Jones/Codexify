import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { claimSocialIdentityUsername } from "@/lib/direct-messages";
import { TIPS, navigationTip } from "./onboardingContent";
import { STEP_KEYS, type StepKey } from "./onboardingTypes";
import { useOnboarding } from "./OnboardingProvider";
import LearningModal from "./LearningModal";

export default function OnboardingWizard({
  step,
  mode,
  onAdvance,
  onClose,
  onFinish,
}: {
  step: StepKey;
  mode: "onboarding" | "tour" | "username";
  onAdvance: (step: StepKey) => Promise<void>;
  onClose: () => void;
  onFinish: () => Promise<void>;
}) {
  const context = useOnboarding()!;
  const [username, setUsername] = useState("");
  const [claimError, setClaimError] = useState("");
  const [busy, setBusy] = useState(false);
  const index = STEP_KEYS.indexOf(step);
  const tip =
    step === "navigation" ? navigationTip(context.mobile) : TIPS.find((t) => t.id === step);
  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
    } catch {
      /* provider displays save error */
    } finally {
      setBusy(false);
    }
  };
  const claim = async () => {
    if (!context.messagingAvailable) return;
    setClaimError("");
    setBusy(true);
    try {
      context.setProfile(await claimSocialIdentityUsername(username));
    } catch (err) {
      setClaimError(err instanceof Error ? err.message : "Username could not be saved.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <LearningModal title="Codexify onboarding" onClose={onClose}>
      <progress
        className="w-full"
        value={index + 1}
        max={STEP_KEYS.length}
        aria-label="Introduction progress"
      />
      <div className="learning-body">
        <p className="learning-muted">
          {context.mobile ? "Phone" : "Desktop"} introduction · {index + 1} / {STEP_KEYS.length}
        </p>
        <h2>
          {tip?.title ??
            (step === "core_surfaces"
              ? "One workspace, several surfaces"
              : "Keep learning at your pace")}
        </h2>
        {tip && (
          <>
            <p>{tip.summary}</p>
            <p className="learning-muted">{tip.body}</p>
          </>
        )}
        {step === "username" && (
          <>
            {context.messagingAvailable ? (
              <>
                <p className="learning-muted">People messaging is a Private Preview capability.</p>
                {context.profile?.username_state === "active" ? (
                  <p role="status">Your username is @{context.profile.username}.</p>
                ) : (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      void claim();
                    }}
                  >
                    <label htmlFor="onboarding-username">Username</label>
                    <Input
                      id="onboarding-username"
                      value={username}
                      autoComplete="off"
                      maxLength={32}
                      onChange={(e) => setUsername(e.target.value.toLowerCase())}
                    />
                    <Button type="submit" disabled={busy}>
                      Claim username
                    </Button>
                  </form>
                )}
                {claimError && <p role="alert">{claimError}</p>}
              </>
            ) : (
              <p>
                People messaging is not enabled in the current runtime/profile. You can continue
                without a username.
              </p>
            )}
          </>
        )}
        {step === "core_surfaces" && (
          <div className="learning-grid">
            {TIPS.filter((t) =>
              [
                "guardian",
                "projects",
                "documents",
                "gallery",
                "dashboard",
                "settings",
                "people",
              ].includes(t.id)
            ).map((t) => (
              <article className="learning-tip" key={t.id}>
                <strong>{t.title}</strong>
                <p className="learning-muted">{t.body}</p>
                {t.requiredCapability && (
                  <small>
                    {context.messagingAvailable
                      ? "Private Preview"
                      : "Unavailable in this runtime/profile"}
                  </small>
                )}
              </article>
            ))}
          </div>
        )}
        {step === "help" && (
          <>
            <p>
              Open Codexify Tips whenever you need a reference. Settings → Help & Learning lets you
              resume or restart setup, try the current device tour, and choose whether contextual
              tips are enabled.
            </p>
            <Button variant="ghost" onClick={context.openTips}>
              Open Codexify Tips
            </Button>
          </>
        )}
        {context.error && <p role="alert">{context.error}</p>}
      </div>
      <footer className="learning-footer">
        <Button variant="ghost" onClick={onClose}>
          Skip for now
        </Button>
        <div className="learning-actions">
          <Button
            variant="ghost"
            disabled={
              busy ||
              index === 0 ||
              mode === "username" ||
              (mode === "tour" && step === "navigation")
            }
            onClick={() => {
              void run(() => onAdvance(STEP_KEYS[index - 1]));
            }}
          >
            Back
          </Button>
          <Button
            disabled={busy}
            onClick={() => {
              void run(() =>
                index === STEP_KEYS.length - 1 || mode === "username"
                  ? onFinish()
                  : onAdvance(STEP_KEYS[index + 1])
              );
            }}
          >
            {mode === "username"
              ? "Done"
              : index === STEP_KEYS.length - 1
                ? "Finish"
                : step === "username" && context.profile?.username_state !== "active"
                  ? "Skip username"
                  : "Continue"}
          </Button>
        </div>
      </footer>
    </LearningModal>
  );
}
