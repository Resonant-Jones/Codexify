import React, { createContext, useContext, useState, useEffect } from "react";
import type { ModelConfig, ModelContextValue } from "@/types/model";

const defaultModel: ModelConfig = {
  providerId: "gpt-120b-oss",
  modelId: "gpt-120b-oss",
  displayName: "GPT 120B (OSS)"
};

const ModelContext = createContext<ModelContextValue | undefined>(undefined);

export function ModelProvider({ children, initialModel }: { children: React.ReactNode; initialModel?: ModelConfig }) {
  const [model, setModelRaw] = useState<ModelConfig>(initialModel ?? defaultModel);
  const [recent, setRecent] = useState<ModelConfig[]>([]);
  const availableProviders = [defaultModel /* ...read from config or remote */];

  useEffect(() => {
    // restore from localStorage
    const saved = localStorage.getItem("app:model");
    if (saved) setModelRaw(JSON.parse(saved));
  }, []);

  useEffect(() => {
    localStorage.setItem("app:model", JSON.stringify(model));
    setRecent((r) => {
      const next = [model, ...r.filter((m) => m.modelId !== model.modelId)].slice(0, 6);
      return next;
    });
  }, [model]);

  const setModel = (m: ModelConfig) => setModelRaw(m);

  const value: ModelContextValue = { model, setModel, recent, availableProviders };
  return <ModelContext.Provider value={value}>{children}</ModelContext.Provider>;
}

export function useModel() {
  const ctx = useContext(ModelContext);
  if (!ctx) throw new Error("useModel must be used inside ModelProvider");
  return ctx;
}
