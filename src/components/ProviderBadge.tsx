import React from "react";
import { usePreferredProvider } from "../hooks/usePreferredProvider";

export const ProviderBadge: React.FC = () => {
  const { provider } = usePreferredProvider();
  return (
    <span
      title="Current provider (empty = backend default)"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: 12,
        padding: "2px 8px",
        borderRadius: 999,
        border: "1px solid rgba(0,0,0,0.12)",
        background: "rgba(255,255,255,0.6)",
        backdropFilter: "blur(6px)",
      }}
    >
      <span style={{ opacity: 0.7 }}>provider</span>
      <strong>{provider || "default"}</strong>
    </span>
  );
};

export default ProviderBadge;

