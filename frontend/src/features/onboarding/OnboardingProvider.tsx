import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";
import { useRuntimeRouteCapability } from "@/lib/runtimeRouteCapabilities";
import { fetchOwnSocialIdentity, type DirectMessageSocialProfile } from "@/lib/direct-messages";
import { fetchOnboarding, patchOnboarding } from "./onboardingApi";
import { STEP_KEYS, type OnboardingState, type StepKey } from "./onboardingTypes";
import OnboardingWizard from "./OnboardingWizard";
import TipsCenter from "./TipsCenter";

type Mode = "onboarding" | "tour" | "username";
type Context = {
  state: OnboardingState | null;
  mobile: boolean;
  messagingAvailable: boolean;
  profile: DirectMessageSocialProfile | null;
  setProfile: (profile: DirectMessageSocialProfile) => void;
  incomplete: boolean;
  openTips: () => void;
  resume: () => void;
  restart: () => void;
  restartTour: () => void;
  chooseUsername: () => void;
  save: (changes: Partial<OnboardingState>) => Promise<void>;
  error: string;
};
const LearningContext = createContext<Context | null>(null);
export const useOnboarding = () => useContext(LearningContext);

export default function OnboardingProvider({
  children,
  ready,
  mobile,
}: {
  children: ReactNode;
  ready: boolean;
  mobile: boolean;
}) {
  const [state, setState] = useState<OnboardingState | null>(null);
  const [profile, setProfile] = useState<DirectMessageSocialProfile | null>(null);
  const [step, setStep] = useState<StepKey>("welcome");
  const [mode, setMode] = useState<Mode>("onboarding");
  const [open, setOpen] = useState(false);
  const [tips, setTips] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const deliberateDismissal = useRef(false);
  const [error, setError] = useState("");
  const mounted = useRef(true);
  const pending = useRef<Promise<unknown>>(Promise.resolve());
  const capability = useRuntimeRouteCapability(SUPPORTED_PROFILE_ROUTE_LABELS.DIRECT_MESSAGES);
  const messagingAvailable = capability.state === "available";
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (!ready) {
      setOpen(false);
      return;
    }
    let active = true;
    fetchOnboarding()
      .then((value) => {
        if (!active) return;
        setState(value);
        if (value.status === "not_started" && !deliberateDismissal.current) {
          setStep("welcome");
          setOpen(true);
        }
      })
      .catch((err) => {
        if (active) {
          console.warn("[onboarding] Load failed", err);
          setError("Setup is unavailable. Codexify remains usable.");
        }
      });
    return () => {
      active = false;
    };
  }, [ready]);
  useEffect(() => {
    if (!ready || !messagingAvailable) {
      setProfile(null);
      return;
    }
    let active = true;
    fetchOwnSocialIdentity()
      .then((value) => {
        if (active) setProfile(value);
      })
      .catch((err) => console.warn("[onboarding] Social identity unavailable", err));
    return () => {
      active = false;
    };
  }, [ready, messagingAvailable]);
  const save = (changes: Partial<OnboardingState>) => {
    const task = pending.current
      .catch(() => {})
      .then(() => {
        if (!mounted.current) throw new Error("Account context changed; progress was not saved.");
        return patchOnboarding(changes);
      })
      .then((value) => {
        if (mounted.current) {
          setState(value);
          setError("");
        }
      })
      .catch((err) => {
        if (mounted.current)
          setError(err instanceof Error ? err.message : "Progress was not saved.");
        throw err;
      });
    pending.current = task;
    return task;
  };
  const show = (next: StepKey, nextMode: Mode) => {
    if (!ready) return;
    setTips(false);
    setMode(nextMode);
    setStep(next);
    setOpen(true);
  };
  const resume = () =>
    show(
      state?.last_step_key && STEP_KEYS.includes(state.last_step_key)
        ? state.last_step_key
        : "welcome",
      "onboarding"
    );
  const restart = () => show("welcome", "onboarding");
  const restartTour = () => show("navigation", "tour");
  const close = async () => {
    setOpen(false);
    setDismissed(true);
    deliberateDismissal.current = true;
    if (mode !== "onboarding") return;
    try {
      await save({ status: "skipped", last_step_key: step });
    } catch {
      window.dispatchEvent(
        new CustomEvent("cfy:toast", {
          detail: { message: "Setup closed. Progress was not saved." },
        })
      );
    }
  };
  const advance = async (next: StepKey) => {
    if (mode === "onboarding") await save({ status: "in_progress", last_step_key: next });
    setStep(next);
  };
  const finish = async () => {
    if (mode !== "username")
      await save({
        ...(mode === "onboarding"
          ? { status: "completed" as const, last_step_key: "help" as const }
          : {}),
        ...(mobile ? { mobile_tour_completed: true } : { desktop_tour_completed: true }),
      });
    setDismissed(false);
    setOpen(false);
  };
  return (
    <LearningContext.Provider
      value={{
        state,
        mobile,
        messagingAvailable,
        profile,
        setProfile,
        incomplete:
          state?.status === "skipped" ||
          state?.status === "in_progress" ||
          (dismissed && state?.status === "not_started"),
        resume,
        restart,
        restartTour,
        chooseUsername: () => show("username", "username"),
        openTips: () => {
          setTips(true);
        },
        save,
        error,
      }}
    >
      {children}
      {open && ready && !tips && (
        <OnboardingWizard
          step={step}
          mode={mode}
          onAdvance={advance}
          onClose={() => {
            void close();
          }}
          onFinish={finish}
        />
      )}
      {tips && ready && <TipsCenter onClose={() => setTips(false)} />}
    </LearningContext.Provider>
  );
}
