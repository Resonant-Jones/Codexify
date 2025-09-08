// src/components/ui/hooks/useLocalBool.ts
import { useEffect, useState } from "react";
export function useLocalBool(key: string, defaultVal = false) {
  const [v, setV] = useState<boolean>(() => {
    if (typeof window === "undefined") return defaultVal;
    return localStorage.getItem(key) === "true" ? true : defaultVal;
  });
  useEffect(() => {
    if (typeof window !== "undefined") localStorage.setItem(key, String(v));
  }, [key, v]);
  return [v, setV] as const;
}