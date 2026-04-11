import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  type PersonaConfig,
  type PersonaProfileDraft,
  type ToolsSettings,
  usePersonaStudioLocalDraftState,
} from "./personaStudioStore";
import DiagnosticsPanel from "./components/DiagnosticsPanel";
import TruthMatrix from "./components/TruthMatrix";

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
      aria-pressed={active}
      data-state={active ? "active" : "inactive"}
      className="pill-tab min-w-0 flex-1 px-4 py-3.5 text-[0.95rem]"
    >
      {children}
    </button>
  );
}

const TABS = [
  "Identity",
  "Model",
  "Voice",
  "Prompt",
  "Tools",
  "Retrieval",
  "Truth Matrix",
] as const;

const UTILITY_TABS = ["Profiles", "Diagnostics"] as const;

type UtilityTab = (typeof UTILITY_TABS)[number];

function IdentityEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
          Persona Name
        </label>
        <Input
          className="h-10"
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
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
          Description
        </label>
        <Textarea
          className="min-h-[140px] resize-y"
          value={config.identity.description}
          onChange={(e) =>
            onChange({
              ...config,
              identity: { ...config.identity, description: e.target.value },
            })
          }
          rows={5}
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
  const providerId = "persona-studio-model-provider";
  const modelId = "persona-studio-model-id";

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor={providerId}>
            Provider
          </label>
          <select
            id={providerId}
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
          <label className="text-sm font-medium" htmlFor={modelId}>
            Model
          </label>
          <Input
            id={modelId}
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

export default function PersonaStudioPage() {
  const {
    profiles,
    selectedProfileId,
    activeTab,
    selectedProfile,
    selectedSavedProfile,
    isDirty,
    hasSavedVersion,
    setSelectedProfileId,
    setActiveTab,
    updateSelectedProfile,
    saveSelectedProfile,
    saveSelectedProfileAsNew,
    resetSelectedProfile,
    resetAllLocalPersonaStudioData,
  } = usePersonaStudioLocalDraftState();

  const [isUtilityPaneOpen, setIsUtilityPaneOpen] = React.useState(true);
  const [utilityTab, setUtilityTab] = React.useState<UtilityTab>("Profiles");

  const currentConfig = selectedProfile?.config || null;

  const handleConfigChange = (newConfig: PersonaConfig) => {
    updateSelectedProfile((currentProfile) => ({
      ...currentProfile,
      name: newConfig.identity.name,
      description: newConfig.identity.description,
      config: newConfig,
    }));
  };

  const handleSave = () => {
    saveSelectedProfile();
  };

  const handleSaveAsNew = () => {
    saveSelectedProfileAsNew();
  };

  const handleReset = () => {
    resetSelectedProfile();
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case "Identity":
        return currentConfig ? (
          <IdentityEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Model":
        return currentConfig ? (
          <ModelEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Voice":
        return currentConfig ? (
          <VoiceEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Prompt":
        return currentConfig ? (
          <PromptEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Tools":
        return currentConfig ? (
          <ToolsEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Retrieval":
        return currentConfig ? (
          <RetrievalEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Truth Matrix":
        return <TruthMatrix />;
      default:
        return null;
    }
  };

  return (
    <div className="h-full w-full overflow-auto p-[var(--card-pad)]">
      <div className="flex h-full flex-col gap-6">
        <div
          className="flex flex-col gap-4"
          data-testid="persona-studio-page-header"
        >
          <div className="max-w-3xl space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight">Persona Studio</h1>
            <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
              Configure runtime persona profiles. This is for configuration only — no chat history or memory records are created.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div
              className="glass-pill flex min-w-0 flex-1 items-stretch gap-1.5 overflow-x-auto px-1"
              data-testid="persona-studio-section-tabs"
              style={
                {
                  "--pill-active-text": "var(--text-on-accent)",
                  "--pill-font": "0.92rem",
                  width: "100%",
                  justifyContent: "stretch",
                } as React.CSSProperties
              }
            >
              {TABS.map((tab) => (
                <TabButton
                  key={tab}
                  active={activeTab === tab}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab}
                </TabButton>
              ))}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsUtilityPaneOpen((value) => !value)}
              aria-label={isUtilityPaneOpen ? "Hide utility pane" : "Show utility pane"}
            >
              {isUtilityPaneOpen ? "Hide Utility Pane" : "Show Utility Pane"}
            </Button>
          </div>
        </div>

        <div
          className={`grid min-h-0 flex-1 gap-4 ${
            isUtilityPaneOpen ? "lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)]" : ""
          }`}
        >
          {isUtilityPaneOpen ? (
            <Card
              className="bezel-none flex min-h-0 flex-col overflow-hidden rounded-2xl border"
              role="complementary"
              aria-label="Persona Studio utility pane"
              data-testid="persona-studio-utility-pane"
              style={{
                background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
                borderColor: "var(--panel-border)",
              }}
            >
              <CardHeader className="space-y-3 pb-3">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-base">Utility Pane</CardTitle>
                  <Badge
                    variant="outline"
                    className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                    style={{ borderColor: "var(--panel-border)" }}
                  >
                    {utilityTab}
                  </Badge>
                </div>
                <div
                  className="glass-pill flex w-full items-stretch gap-1.5 overflow-x-auto px-1"
                  data-testid="persona-studio-utility-tabs"
                  style={
                    {
                      "--pill-active-text": "var(--text-on-accent)",
                      "--pill-font": "0.92rem",
                      width: "100%",
                      justifyContent: "stretch",
                    } as React.CSSProperties
                  }
                >
                  {UTILITY_TABS.map((tab) => (
                    <TabButton
                      key={tab}
                      active={utilityTab === tab}
                      onClick={() => setUtilityTab(tab)}
                    >
                      {tab}
                    </TabButton>
                  ))}
                </div>
              </CardHeader>
              <CardContent className="relative min-h-0 flex-1 pt-0">
                <div
                  data-testid="persona-studio-utility-profiles-panel"
                  data-state={utilityTab === "Profiles" ? "active" : "inactive"}
                  className={
                    utilityTab === "Profiles"
                      ? "relative space-y-2"
                      : "sr-only"
                  }
                >
                  {profiles.map((profile) => (
                    <button
                      key={profile.id}
                      type="button"
                      onClick={() => {
                        setSelectedProfileId(profile.id);
                      }}
                      className={`w-full rounded-xl p-3 text-left transition-colors ${
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
                        <span className="text-sm font-medium">{profile.name}</span>
                        {profile.isDefault && (
                          <Badge
                            variant="outline"
                            className="px-1.5 py-0.5 text-[10px]"
                            style={{ borderColor: "var(--panel-border)" }}
                          >
                            Default
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 line-clamp-2 text-xs" style={{ color: "var(--muted)" }}>
                        {profile.description}
                      </p>
                    </button>
                  ))}
                </div>

                <div
                  role="complementary"
                  aria-label="Persona Studio diagnostics"
                  data-testid="persona-studio-diagnostics"
                  data-state={utilityTab === "Diagnostics" ? "active" : "inactive"}
                  className={
                    utilityTab === "Diagnostics"
                      ? "relative h-full"
                      : "sr-only"
                  }
                >
                  <DiagnosticsPanel
                    profile={selectedProfile}
                    config={currentConfig}
                    isDirty={isDirty}
                    hasSavedVersion={hasSavedVersion}
                  />
                </div>
              </CardContent>
            </Card>
          ) : null}

          <Card
            className="bezel-none flex min-h-0 flex-col rounded-2xl border"
            role="region"
            aria-label="Persona Studio editor"
            data-testid="persona-studio-editor"
            data-saved-profile-id={selectedSavedProfile?.id ?? ""}
            data-draft-state={isDirty ? "dirty" : "clean"}
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 98%, transparent)",
              borderColor: "color-mix(in oklab, var(--accent-strong) 18%, var(--panel-border))",
            }}
          >
            <CardHeader className="space-y-4 pb-4">
              <div
                className="rounded-2xl border px-4 py-4"
                data-testid="persona-studio-active-profile-summary"
                style={{
                  background: "color-mix(in srgb, var(--panel-bg) 91%, transparent)",
                  borderColor: "var(--panel-border)",
                }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 space-y-1.5">
                    <div
                      className="text-[11px] font-semibold uppercase tracking-[0.18em]"
                      style={{ color: "var(--muted)" }}
                    >
                      Active profile
                    </div>
                    <CardTitle className="text-lg leading-6">
                      {selectedProfile?.name || "Editor"}
                    </CardTitle>
                    <p className="max-w-2xl text-sm leading-6" style={{ color: "var(--muted)" }}>
                      {selectedProfile?.description ||
                        "Select a persona profile to edit its runtime identity and behavior."}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                    <Badge
                      variant="outline"
                      className="text-[10px] px-2 py-1 uppercase tracking-[0.14em]"
                      style={{
                        borderColor: "var(--panel-border)",
                      }}
                    >
                      {selectedProfile?.isDefault ? "Default profile" : "Custom profile"}
                    </Badge>
                    <Badge
                      variant="outline"
                      className="text-[10px] px-2 py-1 uppercase tracking-[0.14em]"
                      style={{
                        borderColor: "var(--accent)",
                        color: "var(--accent)",
                      }}
                    >
                      Active profile
                    </Badge>
                  </div>
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  <div
                    className="rounded-xl border px-3 py-2"
                    style={{
                      borderColor: "var(--panel-border)",
                      background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                    }}
                  >
                    <div
                      className="text-[11px] font-semibold uppercase tracking-[0.16em]"
                      style={{ color: "var(--muted)" }}
                    >
                      Selection
                    </div>
                    <div className="mt-1 text-sm font-medium">
                      {selectedProfile?.isDefault
                        ? "Default runtime profile"
                        : "Custom runtime profile"}
                    </div>
                  </div>
                  <div
                    className="rounded-xl border px-3 py-2"
                    style={{
                      borderColor: "var(--panel-border)",
                      background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                    }}
                  >
                    <div
                      className="text-[11px] font-semibold uppercase tracking-[0.16em]"
                      style={{ color: "var(--muted)" }}
                    >
                      Status
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2">
                      <Badge
                        variant="outline"
                        className="text-[10px] px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        {selectedProfile?.isDefault ? "Default" : "Custom"}
                      </Badge>
                      <Badge
                        variant="outline"
                        className="text-[10px] px-2 py-1"
                        style={{
                          borderColor: "var(--accent)",
                          color: "var(--accent)",
                        }}
                      >
                        Active
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex min-h-0 flex-1 flex-col space-y-5 pt-0">
              <div
                className="rounded-2xl border p-5"
                style={{
                  background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
                  borderColor: "var(--panel-border)",
                }}
              >
                {renderActiveTab()}
              </div>
            </CardContent>
            <CardFooter className="flex flex-wrap items-center gap-3 pt-0">
              <Button type="button" onClick={handleSave} disabled={!isDirty}>
                Save
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
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={resetAllLocalPersonaStudioData}
                className="whitespace-nowrap"
                aria-label="Reset All Local Persona Studio Data"
                title="Reset All Local Persona Studio Data"
              >
                Reset All Data
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  );
}
