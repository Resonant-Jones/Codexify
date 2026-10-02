import { Button } from "@/components/ui/button";
import { useOnboarding } from "./OnboardingProvider";
export default function HelpAndLearning() {
  const context = useOnboarding();
  if (!context) return null;
  return (
    <section className="learning-setup" aria-label="Help & Learning">
      <h3>Help & Learning</h3>
      <div className="learning-actions">
        <Button variant="ghost" onClick={context.openTips}>
          Open Codexify Tips
        </Button>
        <Button variant="ghost" onClick={context.restart}>
          Restart onboarding
        </Button>
        <Button variant="ghost" onClick={context.restartTour}>
          Restart {context.mobile ? "mobile" : "desktop"} tour
        </Button>
      </div>
      {context.incomplete && (
        <Button variant="ghost" onClick={context.resume}>
          Resume setup
        </Button>
      )}
      <label>
        <input
          type="checkbox"
          checked={context.state?.contextual_tips_enabled ?? false}
          disabled={!context.state}
          onChange={(e) => {
            void context.save({ contextual_tips_enabled: e.target.checked }).catch(() => {});
          }}
        />{" "}
        Contextual tips: {context.state?.contextual_tips_enabled ? "On" : "Off"}
      </label>
      {context.state?.status === "completed" &&
        !(context.mobile
          ? context.state.mobile_tour_completed
          : context.state.desktop_tour_completed) && (
          <p>Try the optional {context.mobile ? "mobile" : "desktop"} tour for this device.</p>
        )}
      {context.error && <p role="status">{context.error}</p>}
    </section>
  );
}
