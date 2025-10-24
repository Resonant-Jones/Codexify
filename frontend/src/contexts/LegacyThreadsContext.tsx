import React from "react";

export type LegacyThreadsContextValue = {
  enabled: boolean;
  isOpen: boolean;
  open: () => void;
  close: () => void;
};

const defaultCtx: LegacyThreadsContextValue = {
  enabled: false,
  isOpen: false,
  open: () => {},
  close: () => {},
};

export const LegacyThreadsContext = React.createContext<LegacyThreadsContextValue>(defaultCtx);

export function useLegacyThreads() {
  return React.useContext(LegacyThreadsContext);
}

export function LegacyThreadsProvider({ value, children }: { value: LegacyThreadsContextValue; children: React.ReactNode }) {
  return <LegacyThreadsContext.Provider value={value}>{children}</LegacyThreadsContext.Provider>;
}

