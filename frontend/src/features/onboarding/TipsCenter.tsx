import { useState } from "react";
import { Button } from "@/components/ui/button";
import { TIPS } from "./onboardingContent";
import { useOnboarding } from "./OnboardingProvider";
import LearningModal from "./LearningModal";
export default function TipsCenter({ onClose }: { onClose: () => void }) {
  const context = useOnboarding()!;
  const [category, setCategory] = useState("All");
  const tips = TIPS.filter(
    (t) =>
      (t.surface === "shared" || t.surface === (context.mobile ? "mobile" : "desktop")) &&
      (!t.requiredCapability || context.messagingAvailable)
  );
  return (
    <LearningModal title="Codexify Tips" onClose={onClose}>
      <div className="learning-body">
        <h2>Learn at your pace</h2>
        <label htmlFor="tips-category">Category</label>
        <select id="tips-category" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option>All</option>
          {Array.from(new Set(tips.map((t) => t.category))).map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <div className="learning-grid">
          {tips
            .filter((t) => category === "All" || t.category === category)
            .map((t) => (
              <details className="learning-tip" key={t.id}>
                <summary>
                  <strong>{t.title}</strong>
                  <p className="learning-muted">{t.summary}</p>
                </summary>
                <p>{t.body}</p>
                {t.requiredCapability && <small>Private Preview · same-node only</small>}
              </details>
            ))}
        </div>
        {!context.messagingAvailable && (
          <p className="learning-muted">People messaging is not enabled in this runtime/profile.</p>
        )}
        <div className="learning-actions">
          <Button variant="ghost" onClick={context.restart}>
            Restart onboarding
          </Button>
          <Button variant="ghost" onClick={context.restartTour}>
            Restart {context.mobile ? "mobile" : "desktop"} tour
          </Button>
        </div>
      </div>
    </LearningModal>
  );
}
