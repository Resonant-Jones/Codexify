import React, { createContext, useState, useEffect } from "react";

interface PersonaContextProps {
  activePersonaId: string;
  setActivePersonaId: (id: string) => void;
  memoryTags: string[];
  setMemoryTags: (tags: string[]) => void;
  recentTags: string[];
  setRecentTags: (tags: string[]) => void;
  debugMode: boolean;
  setDebugMode: (enabled: boolean) => void;
}

export const PersonaContext = createContext<PersonaContextProps>({
  activePersonaId: "default",
  setActivePersonaId: () => {},
  memoryTags: [],
  setMemoryTags: () => {},
  recentTags: [],
  setRecentTags: () => {},
  debugMode: false,
  setDebugMode: () => {},
});

export const PersonaProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [activePersonaId, setActivePersonaId] = useState("default");
  const [memoryTags, setMemoryTags] = useState<string[]>([]);
  const [recentTags, setRecentTags] = useState<string[]>([]);
  const [debugMode, setDebugMode] = useState(false);

  // Load from localStorage
  useEffect(() => {
    const storedPersonaId = localStorage.getItem("activePersonaId");
    const storedTags = localStorage.getItem("memoryTags");
    const storedRecentTags = localStorage.getItem("recentTags");
    const storedDebug = localStorage.getItem("debugMode");

    if (storedPersonaId) setActivePersonaId(storedPersonaId);
    if (storedTags) setMemoryTags(JSON.parse(storedTags));
    if (storedRecentTags) setRecentTags(JSON.parse(storedRecentTags));
    if (storedDebug) setDebugMode(storedDebug === "true");
  }, []);

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem("activePersonaId", activePersonaId);
    localStorage.setItem("memoryTags", JSON.stringify(memoryTags));
    localStorage.setItem("recentTags", JSON.stringify(recentTags));
    localStorage.setItem("debugMode", debugMode.toString());
  }, [activePersonaId, memoryTags, recentTags, debugMode]);

  return (
    <PersonaContext.Provider
      value={{
        activePersonaId,
        setActivePersonaId,
        memoryTags,
        setMemoryTags,
        recentTags,
        setRecentTags,
        debugMode,
        setDebugMode,
      }}
    >
      {children}
    </PersonaContext.Provider>
  );
};