import { Button } from "@/components/ui/button";
import { useOnboarding } from "./OnboardingProvider";
export default function PeopleSetupBanner() {
  const context = useOnboarding();
  if (!context) return null;
  if (context.incomplete)
    return (
      <section className="learning-setup" aria-label="Optional Codexify setup">
        <strong>Finish setting up Codexify</strong>
        <p>Resume the optional introduction.</p>
        <Button variant="ghost" onClick={context.resume}>
          Resume setup
        </Button>
      </section>
    );
  if (
    context.state?.status === "completed" &&
    context.messagingAvailable &&
    context.profile?.username_state === "unset"
  )
    return (
      <section className="learning-setup" aria-label="Optional messaging setup">
        <strong>Set up messaging</strong>
        <p>Choose a username so people on this node can find you.</p>
        <Button variant="ghost" onClick={context.chooseUsername}>
          Choose username
        </Button>
      </section>
    );
  return null;
}
