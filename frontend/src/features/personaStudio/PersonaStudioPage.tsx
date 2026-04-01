import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  type PersonaConfig,
  type PersonaProfileDraft,
  type ToolsSettings,
  usePersonaStudioLocalDraftState,
} from "./personaStudioStore";

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

function buildDebugLog(
  profile: PersonaProfileDraft | null,
  config: PersonaConfig | null
): string[] {
  if (!profile || !config) {
    return [
      "[PersonaStudio] Initialized local draft store",
      "[PersonaStudio] Waiting for profile selection",
      "[Config] No profile selected",
    ];
  }

  return [
    "[PersonaStudio] Initialized local draft store",
    `[PersonaStudio] Selected profile: ${profile.id}`,
    `[PersonaStudio] Profile loaded: ${profile.name}`,
    `[Config] Model: ${config.model.provider}/${config.model.model}`,
    `[Config] Temperature: ${config.model.temperature}`,
    `[Config] Voice: ${config.voice.enabled ? config.voice.provider : "disabled"}`,
    `[Config] Retrieval: ${config.retrieval.enabled ? config.retrieval.mode : "disabled"}`,
  ];
}

type PersonaStudioTruthMatrixRow = {
  control: string;
  uiPresent: boolean;
  localDraftState: boolean;
  savedLocally: boolean;
  backendPersisted: boolean;
  appliedToRuntime: boolean;
};

const PERSONA_STUDIO_TRUTH_MATRIX_BASE_TRUTH = {
  uiPresent: true,
  localDraftState: true,
  savedLocally: true,
  backendPersisted: false,
  appliedToRuntime: false,
} as const;

const PERSONA_STUDIO_TRUTH_MATRIX_CONTROLS = [
  "Persona Name",
  "Description",
  "Model Provider",
  "Model ID",
  "Temperature",
  "Generation Top K",
  "Top P",
  "Max Tokens",
  "Voice Enabled",
  "Voice Provider",
  "Voice Preset",
  "Wake Word",
  "Interruptible Voice",
  "System Prompt",
  "Style Notes",
  "Directives",
  "Pinned Tools",
  "Allowed Tools",
  "Skills",
  "Web Permission",
  "Email Permission",
  "Calendar Permission",
  "CLI Permission",
  "Filesystem Permission",
  "Retrieval Enabled",
  "Retrieval Mode",
  "Retrieval Top K",
  "Retrieval Rerank",
] as const;

const PERSONA_STUDIO_TRUTH_MATRIX_ROWS: PersonaStudioTruthMatrixRow[] =
  PERSONA_STUDIO_TRUTH_MATRIX_CONTROLS.map((control) => ({
    control,
    ...PERSONA_STUDIO_TRUTH_MATRIX_BASE_TRUTH,
  }));

function TruthValuePill({ value }: { value: boolean }) {
  return (
    <span
      className="inline-flex min-w-12 justify-center rounded-full border px-2 py-0.5 text-[10px] font-medium"
      style={{
        borderColor: value ? "rgba(34, 197, 94, 0.35)" : "var(--panel-border)",
        background: value ? "rgba(34, 197, 94, 0.12)" : "transparent",
        color: value ? "rgb(74, 222, 128)" : "var(--muted)",
      }}
    >
      {value ? "Yes" : "No"}
    </span>
  );
}

function PersonaStudioTruthMatrix() {
  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
            Truth Matrix
          </h4>
          <p className="text-[11px] leading-tight" style={{ color: "var(--muted)" }}>
            Field-by-field implementation truth for the current Persona Studio page.
            Backend Persisted and Applied to Runtime remain No.
          </p>
        </div>
      </div>

      <div
        className="rounded-lg border overflow-auto"
        style={{
          background: "rgba(0,0,0,0.12)",
          borderColor: "var(--panel-border)",
          maxHeight: "280px",
        }}
      >
        <table
          aria-label="Persona Studio truth matrix"
          className="w-full table-fixed text-[11px]"
        >
          <colgroup>
            <col style={{ width: "30%" }} />
            <col style={{ width: "14%" }} />
            <col style={{ width: "14%" }} />
            <col style={{ width: "14%" }} />
            <col style={{ width: "14%" }} />
            <col style={{ width: "14%" }} />
          </colgroup>
          <thead
            className="sticky top-0 z-10"
            style={{ background: "rgba(0,0,0,0.18)" }}
          >
            <tr>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight"
                style={{ color: "var(--muted)" }}
              >
                Control
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight"
                style={{ color: "var(--muted)" }}
              >
                UI Present
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight"
                style={{ color: "var(--muted)" }}
              >
                Local Draft State
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight"
                style={{ color: "var(--muted)" }}
              >
                Saved Locally
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight"
                style={{ color: "var(--muted)" }}
              >
                Backend Persisted
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight"
                style={{ color: "var(--muted)" }}
              >
                Applied to Runtime
              </th>
            </tr>
          </thead>
          <tbody>
            {PERSONA_STUDIO_TRUTH_MATRIX_ROWS.map((row, index) => (
              <tr
                key={row.control}
                className="border-t"
                style={{
                  borderColor: "var(--panel-border)",
                  background:
                    index % 2 === 0 ? "transparent" : "rgba(255, 255, 255, 0.02)",
                }}
              >
                <th
                  scope="row"
                  className="px-2 py-2 text-left font-medium leading-tight"
                  style={{ color: "var(--text)" }}
                >
                  {row.control}
                </th>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.uiPresent} />
                </td>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.localDraftState} />
                </td>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.savedLocally} />
                </td>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.backendPersisted} />
                </td>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.appliedToRuntime} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DiagnosticsPanel({
  profile,
  config,
  isDirty,
  hasSavedVersion,
}: {
  profile: PersonaProfileDraft | null;
  config: PersonaConfig | null;
  isDirty: boolean;
  hasSavedVersion: boolean;
}) {
  const [debugLog, setDebugLog] = React.useState<string[]>(() =>
    buildDebugLog(profile, config)
  );

  React.useEffect(() => {
    setDebugLog(buildDebugLog(profile, config));
  }, [profile, config]);

  const saveStatusLabel = isDirty
    ? "Unsaved Draft"
    : hasSavedVersion
      ? "Saved Locally"
      : "Seed Draft";

  const saveStatusTone = isDirty ? "warning" : hasSavedVersion ? "saved" : "seed";

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
                  saveStatusTone === "saved"
                    ? "rgba(34, 197, 94, 0.35)"
                    : saveStatusTone === "warning"
                      ? "rgba(234, 179, 8, 0.35)"
                      : "var(--panel-border)",
                background: saveStatusTone === "saved"
                  ? "rgba(34, 197, 94, 0.12)"
                  : saveStatusTone === "warning"
                    ? "rgba(234, 179, 8, 0.12)"
                    : "transparent",
              }}
            >
              {saveStatusLabel}
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

      <PersonaStudioTruthMatrix />

    </div>
  );
}

export default function PersonaStudioPage() {
  const {
    profiles,
    selectedProfileId,
    activeTab,
    selectedProfile,
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
              {profiles.map((profile) => (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => {
                    setSelectedProfileId(profile.id);
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
                  disabled={!isDirty}
                >
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
                hasSavedVersion={hasSavedVersion}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
