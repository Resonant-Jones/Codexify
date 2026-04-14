import { CSSProperties, useState } from "react";
import { buildAuthenticatedFetchInit } from "@/lib/api";
import { resolveApiUrl, resolveSharePublicUrl } from "@/lib/runtimeConfig";
import { getMobileTapTargetStyle } from "@/components/persona/layout/mobileInteractionContract";
import { usePressFeedback } from "@/hooks/usePressFeedback";

type ShareButtonProps = {
  targetType: "thread" | "document";
  targetId: number;
  className?: string;
  style?: CSSProperties;
  dataState?: "active" | "inactive";
  isPhoneShell?: boolean;
};

type CopyMethod = "clipboard" | "execCommand" | "prompt" | "none";

async function copyTextWithFallback(text: string): Promise<CopyMethod> {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return "clipboard";
    } catch {
      // Continue to fallback copy methods below.
    }
  }

  if (typeof document !== "undefined" && typeof document.execCommand === "function") {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    try {
      if (document.execCommand("copy")) return "execCommand";
    } catch {
      // Continue to fallback prompt below.
    } finally {
      document.body.removeChild(textarea);
    }
  }

  if (typeof window !== "undefined" && typeof window.prompt === "function") {
    try {
      window.prompt("Copy link:", text);
      return "prompt";
    } catch {
      // No-op. We'll return "none" below.
    }
  }

  return "none";
}

export function ShareButton({
  targetType,
  targetId,
  className,
  style,
  dataState,
  isPhoneShell = false,
}: ShareButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const pressFeedback = usePressFeedback({ enabled: isPhoneShell && !isLoading });

  const handleShare = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        resolveApiUrl("/api/share"),
        buildAuthenticatedFetchInit({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            target_type: targetType,
            target_id: targetId,
          }),
        })
      );

      if (!response.ok) {
        throw new Error(`Failed to create share link: ${response.status}`);
      }

      const data = await response.json();
      if (!data.ok) {
        throw new Error(data.detail || "Failed to create share link");
      }

      const fullUrl = resolveSharePublicUrl(String(data.url || ""));

      // Copy to clipboard with fallback support for non-secure or restricted contexts.
      const copyMethod = await copyTextWithFallback(fullUrl);
      if (copyMethod === "clipboard" || copyMethod === "execCommand") {
        setToastMessage(`Share link copied! ${fullUrl}`);
      } else if (copyMethod === "prompt") {
        setToastMessage(`Share link ready to copy: ${fullUrl}`);
      } else {
        setToastMessage(`Share link created: ${fullUrl}`);
      }
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
    } catch (error) {
      console.error("Share create failed:", error);
      const message = error instanceof Error ? error.message : "Failed to create share link";
      setToastMessage(message);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={handleShare}
        disabled={isLoading}
        {...pressFeedback.getPressFeedbackProps({
          className,
          style: {
            ...getMobileTapTargetStyle(isPhoneShell),
            padding: "6px 12px",
            borderRadius: 6,
            border: "1px solid var(--panel-border)",
            backgroundColor: "var(--panel-bg)",
            cursor: isLoading ? "not-allowed" : "pointer",
            fontSize: 13,
            fontWeight: 500,
            color: isLoading ? "var(--text-subtle)" : "var(--text)",
            transition: "all 200ms",
            opacity: isLoading ? 0.6 : 1,
            ...style,
          },
        })}
        data-state={dataState}
      >
        {isLoading ? "Creating..." : "Share"}
      </button>

      {showToast && (
        <div
          style={{
            position: "fixed",
            bottom: 20,
            right: 20,
            backgroundColor: "var(--panel-sheet, var(--panel-bg))",
            color: "var(--text)",
            border: "1px solid var(--panel-border)",
            padding: "12px 16px",
            borderRadius: 8,
            fontSize: 13,
            maxWidth: 300,
            boxShadow: "0 10px 25px rgba(0,0,0,.2)",
            zIndex: 1000,
            animation: "slideIn 200ms ease-out",
          }}
        >
          {toastMessage}
        </div>
      )}

      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </>
  );
}
