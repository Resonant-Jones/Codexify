import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  type PersonaConfig,
  usePersonaStudioLocalDraftState,
} from "./personaStudioStore";
import PersonaVoicePanel from "./components/PersonaVoicePanel";
import StudioGuidePanel from "./components/StudioGuidePanel";
import TruthMatrix from "./components/TruthMatrix";
import PersonaStudioRail from "./PersonaStudioRail";
import PersonaProfileSelector from "./PersonaProfileSelector";

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
  } = usePersonaStudioLocalDraftState();

  const handleTabChange = (tab: (typeof TABS)[number]) => {
    setActiveTab(tab);
  };

  const currentConfig = selectedProfile?.config ?? null;

  const handleSave = () => {
    if (selectedProfile) {
      saveSelectedProfile();
    }
  };

  const handleSaveAsNew = () => {
    if (selectedProfile) {
      saveSelectedProfileAsNew();
    }
  };

  const handleReset = () => {
    resetSelectedProfile();
  };

  const resetAllLocalPersonaStudioData = React.useCallback(() => {
    if (window.confirm("Reset all local Persona Studio data?")) {
      localStorage.removeItem("personaStudio");
      window.location.reload();
    }
  }, []);

  const renderActiveTab = () => {
    if (!currentConfig) {
      return (
        <div className="flex items-center justify-center py-12 text-sm" style={{ color: "var(--muted)" }}>
          Select a profile to begin editing.
        </div>
      );
    }

    const onChange = (config: PersonaConfig) => {
      if (selectedProfile) {
        updateSelectedProfile((currentProfile) => ({
          ...currentProfile,
          name: config.identity.name,
          description: config.identity.description,
          config,
        }));
      }
    };

    switch (activeTab) {
      case "Identity":
        return <IdentityEditor config={currentConfig} onChange={onChange} />;
      case "Model":
        return <ModelEditor config={currentConfig} onChange={onChange} />;
      case "Voice":
        return <PersonaVoicePanel config={currentConfig} onChange={onChange} />;
      case "Prompt":
        return <PromptEditor config={currentConfig} onChange={onChange} />;
      case "Tools":
        return <ToolsEditor config={currentConfig} onChange={onChange} />;
      case "Retrieval":
        return <RetrievalEditor config={currentConfig} onChange={onChange} />;
      case "Truth Matrix":
        return <TruthMatrix config={currentConfig} />;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden" data-testid="persona-studio-page" style={{ background: "var(--bg)" }}>
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden px-6 pt-6 pb-6">
        <section
          className="flex min-h-0 flex-1 flex-col overflow-x-hidden overflow-y-auto rounded-[var(--card-radius)] border p-[var(--card-pad)]"
          data-testid="persona-studio-shell"
          style={{
            background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
            borderColor: "var(--panel-border)",
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), inset 0 -1px 0 rgba(0,0,0,0.16)",
          }}
        >
          <div
            className="grid min-h-0 flex-1 gap-[var(--shell-gap)] lg:items-stretch lg:grid-cols-[minmax(0,var(--persona-studio-editor-flex))_minmax(var(--persona-studio-preview-min),var(--persona-studio-preview-flex))_minmax(var(--persona-studio-preview-min),var(--persona-studio-preview-flex))]"
            data-testid="persona-studio-editor-two-lane-layout"
          >
            <div className="flex min-h-0 min-w-0 flex-col gap-[var(--shell-gap)] overflow-y-auto pr-1" data-testid="persona-studio-configuration-lane">
              <div className="space-y-4" data-testid="persona-studio-shell-header">
                <div>
                  <h1 className="text-2xl font-semibold" style={{ color: "var(--text)" }}>
                    Persona Studio
                  </h1>
                  <p className="mt-1 text-sm leading-6" style={{ color: "var(--muted)" }}>
                    Configure reusable agent profiles.
                  </p>
                </div>
                <div
                  className="glass-pill flex w-full items-stretch gap-1.5 overflow-x-auto px-1"
                  data-testid="persona-studio-tabs"
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
                    <TabButton key={tab} active={activeTab === tab} onClick={() => handleTabChange(tab)}>
                      {tab}
                    </TabButton>
                  ))}
                </div>
              </div>

              <div
                className="rounded-[var(--tile-radius)] border px-4 py-4"
                role="region"
                aria-label="Persona Studio editor"
                data-testid="persona-studio-editor"
                data-saved-profile-id={selectedSavedProfile?.id ?? ""}
                data-draft-state={isDirty ? "dirty" : "clean"}
                style={{
                  background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
                  borderColor: "color-mix(in oklab, var(--accent-strong) 18%, var(--panel-border))",
                }}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1" />
                  <Badge className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]" style={{ borderColor: "var(--panel-border)" }}>
                    {activeTab}
                  </Badge>
                </div>

                <div className="mt-4 rounded-[var(--tile-radius)] border px-3 py-3" style={{ borderColor: "var(--panel-border)", background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)" }}>
                  {renderActiveTab()}
                </div>

              </div>

              <PersonaProfileSelector
                profiles={profiles}
                selectedProfileId={selectedProfileId}
                onSelectProfile={setSelectedProfileId}
                selectedProfile={selectedProfile}
                isDirty={isDirty}
                hasSavedVersion={hasSavedVersion}
                onSave={handleSave}
                onSaveAsNew={handleSaveAsNew}
                onReset={handleReset}
                onResetAll={resetAllLocalPersonaStudioData}
              />
            </div>

            <div
              className="flex min-h-0 min-w-0 flex-col lg:sticky lg:top-0 lg:max-h-full"
              data-testid="persona-studio-rail-lane"
            >
              <PersonaStudioRail
                selectedProfile={selectedProfile}
                config={currentConfig}
                isDirty={isDirty}
                hasSavedVersion={hasSavedVersion}
              />
            </div>

            <div
              className="flex min-h-0 min-w-0 flex-col lg:sticky lg:top-0 lg:max-h-full"
              data-testid="persona-studio-guide-lane"
            >
              <StudioGuidePanel config={currentConfig} />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
