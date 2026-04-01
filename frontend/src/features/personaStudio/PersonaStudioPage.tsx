import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type PersonaProfile = {
  id: string;
  name: string;
  description: string;
  isDefault?: boolean;
};

type ModelSettings = {
  provider: string;
  model: string;
  temperature: number;
  topK: number;
  topP: number;
  maxTokens: number;
};

type VoiceSettings = {
  enabled: boolean;
  provider: string;
  voicePreset: string;
  speed: number;
  wakeWord: string;
  interruptible: boolean;
};

type PromptSettings = {
  systemPrompt: string;
  styleNotes: string;
  directives: string;
};

type ToolsSettings = {
  pinnedTools: string[];
  allowedTools: string[];
  skills: string[];
  permissions: {
    web: boolean;
    email: boolean;
    calendar: boolean;
    cli: boolean;
    filesystem: boolean;
  };
};

type RetrievalSettings = {
  enabled: boolean;
  mode: string;
  topK: number;
  rerank: boolean;
};

type PersonaConfig = {
  identity: {
    name: string;
    description: string;
  };
  model: ModelSettings;
  voice: VoiceSettings;
  prompt: PromptSettings;
  tools: ToolsSettings;
  permissions: ToolsSettings;
  retrieval: RetrievalSettings;
};

const MOCK_PROFILES: PersonaProfile[] = [
  {
    id: "profile-1",
    name: "Guardian Default",
    description: "Default guardian persona for general assistance",
    isDefault: true,
  },
  {
    id: "profile-2",
    name: "Code Assistant",
    description: "Specialized for code review and programming tasks",
  },
  {
    id: "profile-3",
    name: "Research Partner",
    description: "Focused on research and information synthesis",
  },
];

const MOCK_CONFIG: Record<string, PersonaConfig> = {
  "profile-1": {
    identity: {
      name: "Guardian Default",
      description: "Default guardian persona for general assistance",
    },
    model: {
      provider: "openai",
      model: "gpt-4o",
      temperature: 0.7,
      topK: 40,
      topP: 0.95,
      maxTokens: 4096,
    },
    voice: {
      enabled: true,
      provider: "elevenlabs",
      voicePreset: "rachel",
      speed: 1.0,
      wakeWord: "Hey Guardian",
      interruptible: true,
    },
    prompt: {
      systemPrompt: "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity.",
      styleNotes: "Use a warm, encouraging tone. Favor questions over statements when appropriate.",
      directives: "Always prioritize user privacy. Never share sensitive information without explicit permission.",
    },
    tools: {
      pinnedTools: ["web-search", "calculator", "code-interpreter"],
      allowedTools: ["web-search", "calculator", "code-interpreter", "file-reader"],
      skills: ["critical-thinking", "creative-brainstorming"],
      permissions: {
        web: true,
        email: false,
        calendar: false,
        cli: false,
        filesystem: true,
      },
    },
    retrieval: {
      enabled: true,
      mode: "hybrid",
      topK: 10,
      rerank: true,
    },
  },
  "profile-2": {
    identity: {
      name: "Code Assistant",
      description: "Specialized for code review and programming tasks",
    },
    model: {
      provider: "anthropic",
      model: "claude-sonnet-4-20250514",
      temperature: 0.3,
      topK: 20,
      topP: 0.9,
      maxTokens: 8192,
    },
    voice: {
      enabled: false,
      provider: "elevenlabs",
      voicePreset: "matt",
      speed: 1.0,
      wakeWord: "",
      interruptible: true,
    },
    prompt: {
      systemPrompt: "You are an expert code assistant. Provide clear, concise, and accurate code solutions with explanation.",
      styleNotes: "Be precise and technical. Include code examples where helpful.",
      directives: "Always verify code syntax before presenting. Flag potential security issues.",
    },
    tools: {
      pinnedTools: ["code-interpreter", "git", "terminal"],
      allowedTools: ["code-interpreter", "git", "terminal", "web-search", "file-reader"],
      skills: ["code-review", "debugging", "architecture-design"],
      permissions: {
        web: true,
        email: false,
        calendar: false,
        cli: true,
        filesystem: true,
      },
    },
    retrieval: {
      enabled: true,
      mode: "semantic",
      topK: 5,
      rerank: false,
    },
  },
  "profile-3": {
    identity: {
      name: "Research Partner",
      description: "Focused on research and information synthesis",
    },
    model: {
      provider: "openai",
      model: "gpt-4-turbo",
      temperature: 0.5,
      topK: 60,
      topP: 0.97,
      maxTokens: 16384,
    },
    voice: {
      enabled: true,
      provider: "elevenlabs",
      voicePreset: "aria",
      speed: 0.9,
      wakeWord: "Hey Research",
      interruptible: true,
    },
    prompt: {
      systemPrompt: "You are a research partner specializing in information synthesis and critical analysis.",
      styleNotes: "Present information in organized, cited format. Distinguish between facts and interpretations.",
      directives: "Cite sources when available. Clearly state uncertainty when information is incomplete.",
    },
    tools: {
      pinnedTools: ["web-search", "academic-search", "note-taking"],
      allowedTools: ["web-search", "academic-search", "note-taking", "calculator"],
      skills: ["literature-review", "meta-analysis", "synthesis"],
      permissions: {
        web: true,
        email: false,
        calendar: false,
        cli: false,
        filesystem: true,
      },
    },
    retrieval: {
      enabled: true,
      mode: "hybrid",
      topK: 20,
      rerank: true,
    },
  },
};

type EditorTab = "identity" | "model" | "voice" | "prompt" | "tools" | "retrieval";

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
        active
          ? "bg-[var(--accent)] text-[var(--text-on-accent)]"
          : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--panel-hover)]"
      }`}
      style={{
        background: active ? "var(--accent)" : undefined,
        color: active ? "var(--text-on-accent)" : undefined,
      }}
    >
      {children}
    </button>
  );
}

function IdentityEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">Persona Name</label>
        <Input
          value={config.identity.name}
          onChange={(e) =>
            onChange({
              ...config,
              identity: { ...config.identity, name: e.target.value },
            })
          }
          placeholder="Enter persona name"
        />
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium">Description</label>
        <Textarea
          value={config.identity.description}
          onChange={(e) =>
            onChange({
              ...config,
              identity: { ...config.identity, description: e.target.value },
            })
          }
          rows={3}
          placeholder="Describe this persona"
        />
      </div>
    </div>
  );
}

function ModelEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Provider</label>
          <select
            className="w-full h-9 px-3 rounded-md border text-sm"
            style={{
              background: "transparent",
              borderColor: "var(--panel-border)",
              color: "var(--text)",
            }}
            value={config.model.provider}
            onChange={(e) =>
              onChange({
                ...config,
                model: { ...config.model, provider: e.target.value },
              })
            }
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="google">Google</option>
            <option value="local">Local</option>
          </select>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Model</label>
          <Input
            value={config.model.model}
            onChange={(e) =>
              onChange({
                ...config,
                model: { ...config.model, model: e.target.value },
              })
            }
            placeholder="e.g., gpt-4o"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Temperature</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={config.model.temperature}
              onChange={(e) =>
                onChange({
                  ...config,
                  model: { ...config.model, temperature: parseFloat(e.target.value) },
                })
              }
              className="flex-1"
            />
            <span className="text-sm w-12 text-right">{config.model.temperature}</span>
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Max Tokens</label>
          <Input
            type="number"
            value={config.model.maxTokens}
            onChange={(e) =>
              onChange({
                ...config,
                model: { ...config.model, maxTokens: parseInt(e.target.value) || 0 },
              })
            }
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Generation Top K</label>
          <Input
            type="number"
            value={config.model.topK}
            onChange={(e) =>
              onChange({
                ...config,
                model: { ...config.model, topK: parseInt(e.target.value) || 0 },
              })
            }
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Top P</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={config.model.topP}
              onChange={(e) =>
                onChange({
                  ...config,
                  model: { ...config.model, topP: parseFloat(e.target.value) },
                })
              }
              className="flex-1"
            />
            <span className="text-sm w-12 text-right">{config.model.topP}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function VoiceEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={config.voice.enabled}
            onChange={(e) =>
              onChange({
                ...config,
                voice: { ...config.voice, enabled: e.target.checked },
              })
            }
            className="sr-only peer"
          />
          <div className="w-9 h-5 bg-[var(--panel-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent)]"></div>
        </label>
        <span className="text-sm font-medium">Voice Enabled</span>
      </div>

      {config.voice.enabled && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Provider</label>
              <select
                className="w-full h-9 px-3 rounded-md border text-sm"
                style={{
                  background: "transparent",
                  borderColor: "var(--panel-border)",
                  color: "var(--text)",
                }}
                value={config.voice.provider}
                onChange={(e) =>
                  onChange({
                    ...config,
                    voice: { ...config.voice, provider: e.target.value },
                  })
                }
              >
                <option value="elevenlabs">ElevenLabs</option>
                <option value="aws">AWS Polly</option>
                <option value="google">Google TTS</option>
                <option value="azure">Azure Speech</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Voice Preset / Voice ID</label>
              <Input
                value={config.voice.voicePreset}
                onChange={(e) =>
                  onChange({
                    ...config,
                    voice: { ...config.voice, voicePreset: e.target.value },
                  })
                }
                placeholder="e.g., rachel"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Speed</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={config.voice.speed}
                  onChange={(e) =>
                    onChange({
                      ...config,
                      voice: { ...config.voice, speed: parseFloat(e.target.value) },
                    })
                  }
                  className="flex-1"
                />
                <span className="text-sm w-12 text-right">{config.voice.speed}x</span>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Wake Word</label>
              <Input
                value={config.voice.wakeWord}
                onChange={(e) =>
                  onChange({
                    ...config,
                    voice: { ...config.voice, wakeWord: e.target.value },
                  })
                }
                placeholder="e.g., Hey Guardian"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.voice.interruptible}
                onChange={(e) =>
                  onChange({
                    ...config,
                    voice: { ...config.voice, interruptible: e.target.checked },
                  })
                }
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-[var(--panel-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent)]"></div>
            </label>
            <span className="text-sm font-medium">Interruptible</span>
          </div>
        </>
      )}
    </div>
  );
}

function PromptEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">System Prompt</label>
        <Textarea
          value={config.prompt.systemPrompt}
          onChange={(e) =>
            onChange({
              ...config,
              prompt: { ...config.prompt, systemPrompt: e.target.value },
            })
          }
          rows={6}
          placeholder="Enter the system prompt that defines this persona's behavior"
        />
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium">Style Notes</label>
        <Textarea
          value={config.prompt.styleNotes}
          onChange={(e) =>
            onChange({
              ...config,
              prompt: { ...config.prompt, styleNotes: e.target.value },
            })
          }
          rows={3}
          placeholder="Notes about tone, manner, and communication style"
        />
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium">Directives</label>
        <Textarea
          value={config.prompt.directives}
          onChange={(e) =>
            onChange({
              ...config,
              prompt: { ...config.prompt, directives: e.target.value },
            })
          }
          rows={3}
          placeholder="Operational directives and constraints"
        />
      </div>
    </div>
  );
}

function ToolsEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  const [newPinnedTool, setNewPinnedTool] = React.useState("");
  const [newAllowedTool, setNewAllowedTool] = React.useState("");
  const [newSkill, setNewSkill] = React.useState("");

  const addPinnedTool = () => {
    if (newPinnedTool.trim() && !config.tools.pinnedTools.includes(newPinnedTool.trim())) {
      onChange({
        ...config,
        tools: {
          ...config.tools,
          pinnedTools: [...config.tools.pinnedTools, newPinnedTool.trim()],
        },
      });
      setNewPinnedTool("");
    }
  };

  const removePinnedTool = (tool: string) => {
    onChange({
      ...config,
      tools: {
        ...config.tools,
        pinnedTools: config.tools.pinnedTools.filter((t) => t !== tool),
      },
    });
  };

  const addAllowedTool = () => {
    if (newAllowedTool.trim() && !config.tools.allowedTools.includes(newAllowedTool.trim())) {
      onChange({
        ...config,
        tools: {
          ...config.tools,
          allowedTools: [...config.tools.allowedTools, newAllowedTool.trim()],
        },
      });
      setNewAllowedTool("");
    }
  };

  const removeAllowedTool = (tool: string) => {
    onChange({
      ...config,
      tools: {
        ...config.tools,
        allowedTools: config.tools.allowedTools.filter((t) => t !== tool),
      },
    });
  };

  const addSkill = () => {
    if (newSkill.trim() && !config.tools.skills.includes(newSkill.trim())) {
      onChange({
        ...config,
        tools: {
          ...config.tools,
          skills: [...config.tools.skills, newSkill.trim()],
        },
      });
      setNewSkill("");
    }
  };

  const removeSkill = (skill: string) => {
    onChange({
      ...config,
      tools: {
        ...config.tools,
        skills: config.tools.skills.filter((s) => s !== skill),
      },
    });
  };

  const togglePermission = (key: keyof ToolsSettings["permissions"]) => {
    onChange({
      ...config,
      tools: {
        ...config.tools,
        permissions: {
          ...config.tools.permissions,
          [key]: !config.tools.permissions[key],
        },
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <label className="text-sm font-medium">Pinned Tools</label>
        <div className="flex flex-wrap gap-2">
          {config.tools.pinnedTools.map((tool) => (
            <Badge
              key={tool}
              variant="outline"
              className="px-2 py-1 text-xs"
              style={{ borderColor: "var(--panel-border)" }}
            >
              {tool}
              <button
                type="button"
                onClick={() => removePinnedTool(tool)}
                className="ml-1.5 text-[var(--muted)] hover:text-[var(--text)]"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={newPinnedTool}
            onChange={(e) => setNewPinnedTool(e.target.value)}
            placeholder="Add pinned tool"
            className="flex-1"
            onKeyDown={(e) => e.key === "Enter" && addPinnedTool()}
          />
          <Button type="button" size="sm" variant="ghost" onClick={addPinnedTool}>
            Add
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        <label className="text-sm font-medium">Allowed Tools</label>
        <div className="flex flex-wrap gap-2">
          {config.tools.allowedTools.map((tool) => (
            <Badge
              key={tool}
              variant="outline"
              className="px-2 py-1 text-xs"
              style={{ borderColor: "var(--panel-border)" }}
            >
              {tool}
              <button
                type="button"
                onClick={() => removeAllowedTool(tool)}
                className="ml-1.5 text-[var(--muted)] hover:text-[var(--text)]"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={newAllowedTool}
            onChange={(e) => setNewAllowedTool(e.target.value)}
            placeholder="Add allowed tool"
            className="flex-1"
            onKeyDown={(e) => e.key === "Enter" && addAllowedTool()}
          />
          <Button type="button" size="sm" variant="ghost" onClick={addAllowedTool}>
            Add
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        <label className="text-sm font-medium">Skills</label>
        <div className="flex flex-wrap gap-2">
          {config.tools.skills.map((skill) => (
            <Badge
              key={skill}
              variant="outline"
              className="px-2 py-1 text-xs"
              style={{ borderColor: "var(--panel-border)" }}
            >
              {skill}
              <button
                type="button"
                onClick={() => removeSkill(skill)}
                className="ml-1.5 text-[var(--muted)] hover:text-[var(--text)]"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={newSkill}
            onChange={(e) => setNewSkill(e.target.value)}
            placeholder="Add skill"
            className="flex-1"
            onKeyDown={(e) => e.key === "Enter" && addSkill()}
          />
          <Button type="button" size="sm" variant="ghost" onClick={addSkill}>
            Add
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        <label className="text-sm font-medium">Permissions</label>
        <div className="grid grid-cols-2 gap-3">
          {(
            [
              ["web", "Web Access"],
              ["email", "Email"],
              ["calendar", "Calendar"],
              ["cli", "CLI"],
              ["filesystem", "Filesystem"],
            ] as const
          ).map(([key, label]) => (
            <div key={key} className="flex items-center gap-2">
              <input
                type="checkbox"
                id={`perm-${key}`}
                checked={config.tools.permissions[key]}
                onChange={() => togglePermission(key)}
                className="rounded"
              />
              <label htmlFor={`perm-${key}`} className="text-sm">
                {label}
              </label>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RetrievalEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={config.retrieval.enabled}
            onChange={(e) =>
              onChange({
                ...config,
                retrieval: { ...config.retrieval, enabled: e.target.checked },
              })
            }
            className="sr-only peer"
          />
          <div className="w-9 h-5 bg-[var(--panel-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent)]"></div>
        </label>
        <span className="text-sm font-medium">Retrieval Enabled</span>
      </div>

      {config.retrieval.enabled && (
        <>
          <div className="space-y-2">
            <label className="text-sm font-medium">Retrieval Mode</label>
            <select
              className="w-full h-9 px-3 rounded-md border text-sm"
              style={{
                background: "transparent",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
              value={config.retrieval.mode}
              onChange={(e) =>
                onChange({
                  ...config,
                  retrieval: { ...config.retrieval, mode: e.target.value },
                })
              }
            >
              <option value="semantic">Semantic</option>
              <option value="hybrid">Hybrid</option>
              <option value="keyword">Keyword</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Retrieval Top K</label>
            <Input
              type="number"
              value={config.retrieval.topK}
              onChange={(e) =>
                onChange({
                  ...config,
                  retrieval: { ...config.retrieval, topK: parseInt(e.target.value) || 0 },
                })
              }
            />
            <p className="text-xs text-[var(--muted)]">
              Number of documents to retrieve (distinct from Generation Top K)
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.retrieval.rerank}
                onChange={(e) =>
                  onChange({
                    ...config,
                    retrieval: { ...config.retrieval, rerank: e.target.checked },
                  })
                }
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-[var(--panel-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent)]"></div>
            </label>
            <span className="text-sm font-medium">Rerank Results</span>
          </div>
        </>
      )}
    </div>
  );
}

function DiagnosticsPanel({
  profile,
  config,
  isDirty,
  saveStatus,
}: {
  profile: PersonaProfile | null;
  config: PersonaConfig | null;
  isDirty: boolean;
  saveStatus: "idle" | "saving" | "saved" | "error";
}) {
  const [debugLog, setDebugLog] = React.useState<string[]>([
    "[PersonaStudio] Initialized mock persona engine",
    "[PersonaStudio] Loaded profile list: 3 profiles",
    "[PersonaStudio] Selected profile: guardian-default",
    "[Config] Model provider: openai",
    "[Config] Temperature: 0.7",
  ]);

  React.useEffect(() => {
    if (!profile || !config) return;
    const logs = [
      `[PersonaStudio] Profile loaded: ${profile.name}`,
      `[Config] Model: ${config.model.provider}/${config.model.model}`,
      `[Config] Temperature: ${config.model.temperature}`,
      `[Config] Voice: ${config.voice.enabled ? config.voice.provider : "disabled"}`,
      `[Config] Retrieval: ${config.retrieval.enabled ? config.retrieval.mode : "disabled"}`,
    ];
    setDebugLog(logs);
  }, [profile, config]);

  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="space-y-3">
        <h3 className="text-sm font-semibold">Diagnostics</h3>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span style={{ color: "var(--muted)" }}>Save Status</span>
            <Badge
              variant="outline"
              className="text-xs"
              style={{
                borderColor:
                  saveStatus === "saved"
                    ? "rgba(34, 197, 94, 0.35)"
                    : saveStatus === "error"
                      ? "rgba(239, 68, 68, 0.35)"
                      : "var(--panel-border)",
                background: saveStatus === "saved"
                  ? "rgba(34, 197, 94, 0.12)"
                  : saveStatus === "error"
                    ? "rgba(239, 68, 68, 0.12)"
                    : "transparent",
              }}
            >
              {saveStatus === "idle" ? "No changes" : saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "Saved" : "Error"}
            </Badge>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span style={{ color: "var(--muted)" }}>Unsaved Changes</span>
            <span
              className={`font-medium ${isDirty ? "text-[var(--warning)]" : ""}`}
              style={{ color: isDirty ? "rgb(234, 179, 8)" : "var(--muted)" }}
            >
              {isDirty ? "Yes" : "No"}
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-2 flex-1 min-h-0">
        <h4 className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
          Effective Config
        </h4>
        <div
          className="rounded-lg border p-3 text-xs font-mono overflow-auto"
          style={{
            background: "rgba(0,0,0,0.12)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            maxHeight: "200px",
          }}
        >
          {config ? (
            <pre className="whitespace-pre-wrap">{JSON.stringify(config, null, 2)}</pre>
          ) : (
            <span style={{ color: "var(--muted)" }}>No profile selected</span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
          Debug Log
        </h4>
        <div
          className="rounded-lg border p-3 text-xs font-mono overflow-auto"
          style={{
            background: "rgba(0,0,0,0.12)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            maxHeight: "150px",
          }}
        >
          {debugLog.map((log, i) => (
            <div key={i}>{log}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function PersonaStudioPage() {
  const [selectedProfileId, setSelectedProfileId] = React.useState<string>(
    MOCK_PROFILES[0].id
  );
  const [activeTab, setActiveTab] = React.useState<EditorTab>("identity");
  const [configs, setConfigs] = React.useState<Record<string, PersonaConfig>>(MOCK_CONFIG);
  const [isDirty, setIsDirty] = React.useState(false);
  const [saveStatus, setSaveStatus] = React.useState<"idle" | "saving" | "saved" | "error">("idle");

  const selectedProfile = MOCK_PROFILES.find((p) => p.id === selectedProfileId) || null;
  const currentConfig = configs[selectedProfileId] || null;

  const handleConfigChange = (newConfig: PersonaConfig) => {
    setConfigs((prev) => ({
      ...prev,
      [selectedProfileId]: newConfig,
    }));
    setIsDirty(true);
    setSaveStatus("idle");
  };

  const handleSave = () => {
    setSaveStatus("saving");
    setTimeout(() => {
      setSaveStatus("saved");
      setIsDirty(false);
    }, 500);
  };

  const handleSaveAsNew = () => {
    const newId = `profile-${Date.now()}`;
    const newProfile: PersonaProfile = {
      id: newId,
      name: `${currentConfig?.identity.name || "Persona"} (Copy)`,
      description: currentConfig?.identity.description || "",
    };
    MOCK_PROFILES.push(newProfile);
    setConfigs((prev) => ({
      ...prev,
      [newId]: JSON.parse(JSON.stringify(currentConfig)),
    }));
    setSelectedProfileId(newId);
    setSaveStatus("saved");
    setIsDirty(false);
  };

  const handleReset = () => {
    setConfigs((prev) => ({
      ...prev,
      [selectedProfileId]: JSON.parse(JSON.stringify(MOCK_CONFIG[selectedProfileId])),
    }));
    setIsDirty(false);
    setSaveStatus("idle");
  };

  return (
    <div className="h-full w-full overflow-auto p-[var(--card-pad)]">
      <div className="h-full flex flex-col">
        <div className="mb-4">
          <h1 className="text-xl font-semibold">Persona Studio</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--muted)" }}>
            Configure runtime persona profiles. This is for configuration only — no chat history or memory records are created.
          </p>
        </div>

        <div className="grid grid-cols-[280px_1fr_320px] gap-4 flex-1 min-h-0">
          <Card
            className="bezel-none rounded-2xl border"
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
              borderColor: "var(--panel-border)",
            }}
          >
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Profiles</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {MOCK_PROFILES.map((profile) => (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => {
                    if (profile.id !== selectedProfileId) {
                      setSelectedProfileId(profile.id);
                      setIsDirty(false);
                      setSaveStatus("idle");
                    }
                  }}
                  className={`w-full text-left p-3 rounded-xl transition-colors ${
                    profile.id === selectedProfileId
                      ? "border-2"
                      : "border border-transparent hover:border-[var(--panel-border)]"
                  }`}
                  style={{
                    background:
                      profile.id === selectedProfileId
                        ? "rgba(255,255,255,0.08)"
                        : "transparent",
                    borderColor:
                      profile.id === selectedProfileId
                        ? "var(--accent)"
                        : "transparent",
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{profile.name}</span>
                    {profile.isDefault && (
                      <Badge
                        variant="outline"
                        className="text-[10px] px-1.5 py-0.5"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        Default
                      </Badge>
                    )}
                  </div>
                  <p
                    className="text-xs mt-1 line-clamp-2"
                    style={{ color: "var(--muted)" }}
                  >
                    {profile.description}
                  </p>
                </button>
              ))}
            </CardContent>
          </Card>

          <Card
            className="bezel-none rounded-2xl border"
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
              borderColor: "var(--panel-border)",
            }}
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  {selectedProfile?.name || "Editor"}
                </CardTitle>
                <div className="flex gap-1">
                  <TabButton
                    active={activeTab === "identity"}
                    onClick={() => setActiveTab("identity")}
                  >
                    Identity
                  </TabButton>
                  <TabButton
                    active={activeTab === "model"}
                    onClick={() => setActiveTab("model")}
                  >
                    Model
                  </TabButton>
                  <TabButton
                    active={activeTab === "voice"}
                    onClick={() => setActiveTab("voice")}
                  >
                    Voice
                  </TabButton>
                  <TabButton
                    active={activeTab === "prompt"}
                    onClick={() => setActiveTab("prompt")}
                  >
                    Prompt
                  </TabButton>
                  <TabButton
                    active={activeTab === "tools"}
                    onClick={() => setActiveTab("tools")}
                  >
                    Tools
                  </TabButton>
                  <TabButton
                    active={activeTab === "retrieval"}
                    onClick={() => setActiveTab("retrieval")}
                  >
                    Retrieval
                  </TabButton>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {currentConfig && (
                <>
                  {activeTab === "identity" && (
                    <IdentityEditor config={currentConfig} onChange={handleConfigChange} />
                  )}
                  {activeTab === "model" && (
                    <ModelEditor config={currentConfig} onChange={handleConfigChange} />
                  )}
                  {activeTab === "voice" && (
                    <VoiceEditor config={currentConfig} onChange={handleConfigChange} />
                  )}
                  {activeTab === "prompt" && (
                    <PromptEditor config={currentConfig} onChange={handleConfigChange} />
                  )}
                  {activeTab === "tools" && (
                    <ToolsEditor config={currentConfig} onChange={handleConfigChange} />
                  )}
                  {activeTab === "retrieval" && (
                    <RetrievalEditor config={currentConfig} onChange={handleConfigChange} />
                  )}
                </>
              )}

              <div
                className="flex items-center gap-3 pt-4 border-t"
                style={{ borderColor: "var(--panel-border)" }}
              >
                <Button
                  type="button"
                  onClick={handleSave}
                  disabled={!isDirty || saveStatus === "saving"}
                >
                  {saveStatus === "saving" ? "Saving..." : "Save"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleSaveAsNew}
                  disabled={!currentConfig}
                >
                  Save As New
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleReset}
                  disabled={!isDirty}
                >
                  Reset
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card
            className="bezel-none rounded-2xl border"
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
              borderColor: "var(--panel-border)",
            }}
          >
            <CardContent className="pt-4">
              <DiagnosticsPanel
                profile={selectedProfile}
                config={currentConfig}
                isDirty={isDirty}
                saveStatus={saveStatus}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
