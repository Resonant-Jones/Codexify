import { useState } from "react";
import { GuardianAPI } from "../lib/guardianApi";

type ShareButtonProps = {
  targetType: "thread" | "document";
  targetId: number;
};

const API_KEY = (import.meta.env.VITE_GUARDIAN_API_KEY ?? "").trim();

export function ShareButton({ targetType, targetId }: ShareButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState("");

  const handleShare = async () => {
    setIsLoading(true);
    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (API_KEY) {
        headers["X-API-Key"] = API_KEY;
      }
      const response = await fetch("/api/share", {
        method: "POST",
        headers,
        body: JSON.stringify({
          target_type: targetType,
          target_id: targetId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create share link: ${response.status}`);
      }

      const data = await response.json();
      if (!data.ok) {
        throw new Error(data.detail || "Failed to create share link");
      }

      // Build full URL
      const baseUrl = window.location.origin;
      const fullUrl = `${baseUrl}${data.url}`;

      // Copy to clipboard
      await navigator.clipboard.writeText(fullUrl);

      // Show success toast
      setToastMessage(`Share link copied! ${fullUrl}`);
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
        style={{
          padding: "6px 12px",
          borderRadius: 6,
          border: "1px solid rgba(0,0,0,.12)",
          backgroundColor: "#fff",
          cursor: isLoading ? "not-allowed" : "pointer",
          fontSize: 13,
          fontWeight: 500,
          color: isLoading ? "rgba(0,0,0,.4)" : "rgba(0,0,0,.7)",
          transition: "all 200ms",
          opacity: isLoading ? 0.6 : 1,
        }}
      >
        {isLoading ? "Creating..." : "Share"}
      </button>

      {showToast && (
        <div
          style={{
            position: "fixed",
            bottom: 20,
            right: 20,
            backgroundColor: "#1f2937",
            color: "#fff",
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
