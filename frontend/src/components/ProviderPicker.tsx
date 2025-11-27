import React, { useEffect, useState } from "react";
import { GuardianAPI } from "../lib/guardianApi";
import {
  getPreferredProvider,
  setPreferredProvider,
  type ProviderName,
} from "../lib/providerPref";

type Props = {
  onSelect?: (provider: ProviderName) => void;
  value?: ProviderName;
  style?: React.CSSProperties;
};

export const ProviderPicker: React.FC<Props> = ({ onSelect, value, style }) => {
  const [caps, setCaps] = useState<{ chat: string[]; embeddings: string[] }>(
    {
      chat: [],
      embeddings: [],
    }
  );
  const [sel, setSel] = useState<ProviderName>(value ?? getPreferredProvider());

  useEffect(() => {
    let mounted = true;
    GuardianAPI.capabilities()
      .then((c) => mounted && setCaps(c))
      .catch(() => mounted && setCaps({ chat: [], embeddings: [] }));
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    // Persist and notify whenever selection changes
    setPreferredProvider(sel ?? null);
    onSelect?.(sel ?? null);
  }, [sel, onSelect]);

  return (
    <label style={{ display: "inline-flex", gap: 8, alignItems: "center", ...style }}>
      <span>Provider</span>
      <select
        value={sel ?? ""}
        onChange={(e) => setSel(e.target.value || null)}
        style={{ padding: 4 }}
      >
        <option value="">default</option>
        {caps.chat.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
    </label>
  );
};

export default ProviderPicker;
