import { useCallback, useEffect, useState } from "react";
import { getPreferredProvider, setPreferredProvider, type ProviderName } from "../lib/providerPref";

// We’ll broadcast changes within the same tab using a tiny CustomEvent.
// Cross-tab sync uses the native "storage" event.
const EVT = "guardian:providerChanged";

export function usePreferredProvider() {
  const [provider, setProviderState] = useState<ProviderName>(getPreferredProvider());

  // Cross-tab updates
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (
        e.key === "guardian.provider.v1"
        || e.key === "guardian.provider_model.v1"
      ) {
        setProviderState(getPreferredProvider());
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // Same-tab updates
  useEffect(() => {
    const onLocal = () => {
      // no payload needed; just re-read localStorage
      setProviderState(getPreferredProvider());
    };
    window.addEventListener(EVT, onLocal as EventListener);
    return () => window.removeEventListener(EVT, onLocal as EventListener);
  }, []);

  const setProvider = useCallback((p: ProviderName) => {
    setPreferredProvider(p);
    setProviderState(p);
    try {
      window.dispatchEvent(new CustomEvent(EVT));
    } catch {
      // no-op
    }
  }, []);

  return { provider, setProvider };
}
