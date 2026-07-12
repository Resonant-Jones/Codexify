const previewEnabled = import.meta.env.VITE_PRIVATE_PREVIEW === "true";
const feedbackEmail = String(import.meta.env.VITE_PREVIEW_FEEDBACK_EMAIL ?? "").trim();

export function PrivatePreviewBanner() {
  if (!previewEnabled) return null;

  const feedbackHref = feedbackEmail
    ? `mailto:${encodeURIComponent(feedbackEmail)}?subject=${encodeURIComponent("Codexify private preview feedback")}`
    : "#feedback";

  return (
    <aside
      aria-label="Private preview notice"
      className="fixed inset-x-0 top-0 z-[2000] flex items-center justify-center gap-3 bg-amber-300 px-4 py-2 text-sm font-medium text-black shadow"
    >
      <span>Private preview — please do not share this link or sensitive data.</span>
      <a className="underline underline-offset-2" href={feedbackHref}>Send feedback</a>
    </aside>
  );
}
