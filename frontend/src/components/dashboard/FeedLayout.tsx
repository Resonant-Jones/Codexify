import * as React from "react";
import { ArrowDown, ArrowUp, SlidersHorizontal } from "lucide-react";
import { FEED_CARDS, normalizeFeedPreferences, useFeedPreferences, type FeedCardId } from "./feedPreferences";
import "./FeedLayout.css";

export default function FeedLayout({ cards }: { cards: Record<FeedCardId, React.ReactNode> }) {
  const { preferences, update, persistent } = useFeedPreferences();
  const [customizing, setCustomizing] = React.useState(false);
  const [announcement, setAnnouncement] = React.useState("");
  const settingsId = React.useId();
  const toggleRef = React.useRef<HTMLButtonElement>(null);
  const visible = preferences.order.filter((id) => !preferences.hidden.includes(id));
  const labelFor = (id: FeedCardId) => FEED_CARDS.find((card) => card.id === id)!.label;

  function move(id: FeedCardId, direction: -1 | 1) {
    const order = [...preferences.order];
    const index = order.indexOf(id);
    const next = index + direction;
    if (next < 0 || next >= order.length) return;
    [order[index], order[next]] = [order[next], order[index]];
    update({ ...preferences, order });
    setAnnouncement(`${labelFor(id)} moved to position ${next + 1} of ${order.length}.`);
  }

  return (
    <section className="feed-layout" aria-label="Feed" data-testid="dashboard-layout" data-dashboard-layout="feed-stack">
      <header className="feed-toolbar">
        <h1 className="text-lg font-semibold">Feed</h1>
        <button ref={toggleRef} type="button" className="pill-tab feed-customize-toggle" aria-expanded={customizing} aria-controls={settingsId} onClick={() => setCustomizing(!customizing)}>
          <SlidersHorizontal size={16} aria-hidden="true" /> Customize Feed
        </button>
      </header>
      <div className="feed-scroll" role="region" aria-label="Feed cards" tabIndex={0} data-testid="feed-scroll">
        {customizing && (
          <section id={settingsId} aria-label="Customize Feed" className="feed-customizer" onKeyDown={(event) => {
            if (event.key === "Escape") { setCustomizing(false); toggleRef.current?.focus(); }
          }}>
            <p className="text-sm opacity-75">Choose your cards and their order.</p>
            <ol className="feed-card-controls">
              {preferences.order.map((id, index) => (
                <li key={id}>
                  <label><input type="checkbox" checked={!preferences.hidden.includes(id)} onChange={(event) => {
                    update({ ...preferences, hidden: event.target.checked ? preferences.hidden.filter((entry) => entry !== id) : [...preferences.hidden, id] });
                  }} />{labelFor(id)}</label>
                  <div className="feed-move-controls">
                    <button type="button" className="pill-tab" aria-label={`Move ${labelFor(id)} up`} disabled={index === 0} onClick={() => move(id, -1)}><ArrowUp size={18} aria-hidden="true" /></button>
                    <button type="button" className="pill-tab" aria-label={`Move ${labelFor(id)} down`} disabled={index === preferences.order.length - 1} onClick={() => move(id, 1)}><ArrowDown size={18} aria-hidden="true" /></button>
                  </div>
                </li>
              ))}
            </ol>
            <div className="feed-customizer-footer">
              <p className="text-xs opacity-75" role="status">{persistent ? "Saved for your account on this device." : "Changes apply for this visit. Saving is currently unavailable."}</p>
              <button type="button" className="pill-tab" onClick={() => { update(normalizeFeedPreferences()); setAnnouncement("Default Feed layout restored."); }}>Reset layout</button>
            </div>
          </section>
        )}
        <p className="sr-only" role="status" aria-live="polite">{announcement}</p>
        <div className="feed-cards" data-layout-mode="feed-stack">
          {visible.map((id) => <article key={id} aria-label={labelFor(id)} data-feed-card={id}>{cards[id]}</article>)}
          {visible.length === 0 && <div className="feed-empty"><h2 className="text-lg font-semibold">Your Feed is clear</h2><p>Open Customize Feed to show cards again.</p></div>}
        </div>
      </div>
    </section>
  );
}
