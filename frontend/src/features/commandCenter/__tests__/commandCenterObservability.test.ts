import { describe, expect, it } from "vitest";

import {
  buildCommandCenterTraceReportModel,
  deriveGuardianRunVerdict,
  type GuardianRunVerdictInput,
} from "../commandCenterObservability";
import { classifyRetrievalPostureTrend, filterRetrievalPostureHistory, limitRetrievalPostureHistory } from "../components/TraceWorkbench";
import type { CommandCenterRagTracePayload } from "../types";
import {
  COMMAND_CENTER_HEALTH_STATES,
  COMMAND_CENTER_RUN_VERDICTS,
  type CommandCenterHealthItem,
  type CommandCenterHealthState,
} from "../types";

// ── Test fixtures ────────────────────────────────────────────────────────

function healthItem(
  key: CommandCenterHealthItem["key"],
  status: CommandCenterHealthState,
  details?: Record<string, unknown> | null
): CommandCenterHealthItem {
  return {
    checkedAt: Date.now(),
    endpoint: `/health/${key === "core" ? "" : key}`,
    error: null,
    httpStatus: 200,
    key,
    label: key.charAt(0).toUpperCase() + key.slice(1),
    details: details ?? null,
    raw: details ? JSON.stringify(details) : null,
    status,
  };
}

function healthyCoreDetails(): Record<string, unknown> {
  return {
    status: "ok",
    supported_profile: {
      name: "v1-local-core-web-mcp",
      version: 1,
      surface: "local-docker-compose-webui",
      valid: true,
      mismatches: [],
      selected_provider: "local",
      selected_provider_supported: true,
      cloud_capable_configuration_present: false,
      release_hold: false,
      expected_provider: "local",
    },
    release_hold: false,
  };
}

function healthyLlmDetails(): Record<string, unknown> {
  return {
    status: "ok",
    provider_truth: {
      configured: true,
      authorized: true,
      discovered_inventory: true,
      discoverable: true,
      selectable: true,
      executable: true,
      egress_allowed: true,
      supported_profile_name: "v1-local-core-web-mcp",
      supported_profile_valid: true,
      supported_profile_mismatches: [],
      supported_profile_approved: true,
      cloud_capable_configuration_present: false,
      attempted: false,
      executed: false,
      completed: false,
    },
    configured_model: "mlx-community/Llama-3.2-3B-Instruct-4bit",
    configured_model_available: true,
    model_resolution: {
      strict: true,
      source: "whooshd_model_profile",
      model: "mlx-community/Llama-3.2-3B-Instruct-4bit",
      advertised_models: ["mlx-community/Llama-3.2-3B-Instruct-4bit"],
    },
  };
}

function allHealthyItems(): CommandCenterHealthItem[] {
  return [
    healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
    healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, healthyLlmDetails()),
  ];
}

function healthyInput(): GuardianRunVerdictInput {
  return {
    healthItems: allHealthyItems(),
    catalogAvailable: true,
    modelInventoryAvailable: true,
  };
}

// ── Existing tests ───────────────────────────────────────────────────────

describe("commandCenterObservability null safety", () => {
  it("handles partial normalized trace payloads without throwing", () => {
    const partialTrace = {
      resolvedThreadId: 42,
      // intentionally omit semantic and graph to mirror partial live payload shapes
    } as unknown as CommandCenterRagTracePayload;

    expect(() =>
      buildCommandCenterTraceReportModel({
        normalizedTrace: partialTrace,
        rawTrace: {
          documents: undefined,
          graph: undefined,
          memory: undefined,
          payload_summary: {},
          retrieval_plan: {},
        },
        run: null,
        unavailableReason: null,
      })
    ).not.toThrow();
  });

  it("keeps report sections available when nested raw-trace fields are missing", () => {
    const model = buildCommandCenterTraceReportModel({
      normalizedTrace: null,
      rawTrace: {
        documents: null,
        graph: null,
        memory: null,
        payload_summary: null,
        retrieval_plan: null,
      },
      run: null,
      unavailableReason: null,
    });

    expect(model.verdict).toBe("Trace available for inspection.");
    expect(model.payloadSummaryRows.length).toBeGreaterThan(0);
    expect(model.markdown).toContain("## Retrieval Outcome");
  });
});

describe("retrieval posture history null safety", () => {
  it("treats missing history arrays as empty", () => {
    expect(filterRetrievalPostureHistory(undefined, "all")).toEqual([]);
    expect(limitRetrievalPostureHistory(undefined, 5)).toEqual([]);
    expect(classifyRetrievalPostureTrend(undefined)).toBe("insufficient_history");
  });
});

// ── Guardian Run Verdict Classifier ──────────────────────────────────────

describe("deriveGuardianRunVerdict", () => {
  it("returns go when all required surfaces agree", () => {
    const verdict = deriveGuardianRunVerdict(healthyInput());

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.GO);
    expect(verdict.blockers).toEqual([]);
    expect(verdict.evidence.length).toBeGreaterThan(0);
    expect(verdict.sourceSurfaces).toContain("/health");
    expect(verdict.sourceSurfaces).toContain("/health/llm");
    expect(verdict.sourceSurfaces).toContain("/api/llm/catalog");
    expect(verdict.sourceSurfaces).toContain("model inventory");
  });

  it("returns proof_needed for configured model not advertised (C00 pattern)", () => {
    const llmDetails = healthyLlmDetails();
    llmDetails.configured_model_available = false;
    llmDetails.model_resolution = {
      strict: true,
      source: "whooshd_model_profile",
      model: "mlx-community/gemma-4-e2b-it-4bit",
      failure_kind: "configured_model_not_advertised_by_whooshd",
      advertised_models: ["mlx-community/Llama-3.2-3B-Instruct-4bit"],
    };
    llmDetails.configured_model = "mlx-community/gemma-4-e2b-it-4bit";

    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
        healthItem("llm", COMMAND_CENTER_HEALTH_STATES.DOWN, llmDetails),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.PROOF_NEEDED);
    expect(verdict.reason).toContain("gemma-4-e2b-it-4bit");
    expect(verdict.blockers.length).toBeGreaterThan(0);
    expect(verdict.blockers[0]).toContain("not advertised");
    expect(verdict.evidence.some((e) => e.includes("Failure kind"))).toBe(true);
  });

  it("returns proof_needed when catalog evidence is missing", () => {
    const input: GuardianRunVerdictInput = {
      healthItems: allHealthyItems(),
      catalogAvailable: false,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.PROOF_NEEDED);
    expect(verdict.reason).toContain("catalog");
  });

  it("returns proof_needed when model inventory evidence is missing", () => {
    const input: GuardianRunVerdictInput = {
      healthItems: allHealthyItems(),
      catalogAvailable: true,
      modelInventoryAvailable: false,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.PROOF_NEEDED);
    expect(verdict.reason).toContain("model inventory");
  });

  it("returns degraded when non-critical observability is incomplete but core surfaces are healthy", () => {
    // All health surfaces present but LLM status is degraded (not down).
    // Provider truth and model resolution are healthy — this is degraded, not down.
    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
        healthItem(
          "llm",
          COMMAND_CENTER_HEALTH_STATES.DEGRADED,
          healthyLlmDetails()
        ),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.DEGRADED);
    expect(verdict.reason).toContain("degraded");
  });

  it("returns hold when supported profile is invalid", () => {
    const invalidCore = healthyCoreDetails();
    (invalidCore.supported_profile as Record<string, unknown>).valid = false;
    (invalidCore.supported_profile as Record<string, unknown>).mismatches = [
      "expected_provider local but selected_provider openai",
    ];

    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.DEGRADED, invalidCore),
        healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, healthyLlmDetails()),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.HOLD);
    expect(verdict.reason).toContain("invalid");
  });

  it("returns hold when release hold is active", () => {
    const heldCore = healthyCoreDetails();
    heldCore.release_hold = true;

    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, heldCore),
        healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, healthyLlmDetails()),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.HOLD);
    expect(verdict.reason).toContain("Release hold");
  });

  it("does not classify /health ok alone as go", () => {
    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
      ],
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).not.toBe(COMMAND_CENTER_RUN_VERDICTS.GO);
  });

  it("does not classify local-only cloud-provider disabled posture as a failure", () => {
    const input = healthyInput();

    const verdict = deriveGuardianRunVerdict(input);

    // Cloud-capable false should not block go
    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.GO);
    // Should not list cloud configuration as a blocker
    expect(
      verdict.blockers.some((b) => b.toLowerCase().includes("cloud"))
    ).toBe(false);
  });

  it("records cloud-capable configuration as evidence without blocking", () => {
    const cloudLlm = healthyLlmDetails();
    (cloudLlm.provider_truth as Record<string, unknown>).cloud_capable_configuration_present =
      true;

    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
        healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, cloudLlm),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.GO);
    expect(
      verdict.evidence.some((e) => e.includes("Cloud-capable"))
    ).toBe(true);
  });

  it("preserves evidence and blocker strings for operator display", () => {
    const verdict = deriveGuardianRunVerdict(healthyInput());

    expect(typeof verdict.reason).toBe("string");
    expect(verdict.reason.length).toBeGreaterThan(0);
    expect(Array.isArray(verdict.evidence)).toBe(true);
    expect(Array.isArray(verdict.blockers)).toBe(true);
    expect(typeof verdict.recommendedAction).toBe("string");
    expect(verdict.recommendedAction.length).toBeGreaterThan(0);
    expect(Array.isArray(verdict.sourceSurfaces)).toBe(true);
  });

  it("returns proof_needed for empty health items", () => {
    const input: GuardianRunVerdictInput = {
      healthItems: [],
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.PROOF_NEEDED);
    expect(verdict.reason).toContain("No health surfaces");
  });

  it("returns proof_needed when provider truth is missing from LLM health", () => {
    const incompleteLlm = {
      status: "ok",
    };

    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
        healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, incompleteLlm),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.PROOF_NEEDED);
    expect(verdict.reason).toContain("Provider truth");
  });

  it("returns hold when core health is down", () => {
    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.DOWN, {
          status: "down",
          supported_profile: { valid: true },
        }),
        healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, healthyLlmDetails()),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.HOLD);
    expect(verdict.reason).toContain("Core health");
  });

  it("returns hold when provider is not approved by supported profile", () => {
    const unapprovedLlm = healthyLlmDetails();
    (unapprovedLlm.provider_truth as Record<string, unknown>).supported_profile_approved =
      false;

    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
        healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, unapprovedLlm),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.HOLD);
    expect(verdict.reason).toContain("not approved");
  });

  it("returns proof_needed when provider is not configured", () => {
    const unconfiguredLlm = healthyLlmDetails();
    (unconfiguredLlm.provider_truth as Record<string, unknown>).configured = false;

    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
        healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, unconfiguredLlm),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.PROOF_NEEDED);
    expect(verdict.reason).toContain("not configured");
  });

  it("returns degraded when LLM status is degraded but truth surfaces agree", () => {
    // LLM health status is degraded but provider truth, model resolution,
    // and executability are all healthy — returns degraded, not go.
    const input: GuardianRunVerdictInput = {
      healthItems: [
        healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
        healthItem(
          "llm",
          COMMAND_CENTER_HEALTH_STATES.DEGRADED,
          healthyLlmDetails()
        ),
      ],
      catalogAvailable: true,
      modelInventoryAvailable: true,
    };

    const verdict = deriveGuardianRunVerdict(input);

    // Degraded LLM status with healthy provider truth and model → degraded
    expect(verdict.verdict).toBe(COMMAND_CENTER_RUN_VERDICTS.DEGRADED);
  });
});
