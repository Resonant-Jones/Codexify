/** ADR-095 v1 response projection; Guardian remains the configuration authority. */
export type ConfigurationEvidence = "declared" | "resolved" | "observed" | "unavailable";

type EvidenceSection<Owner extends string, Reason extends string> = {
  evidence: ConfigurationEvidence;
  owner: Owner;
  unavailable_reason: Reason | null;
};

export type SupportedProfileSection = EvidenceSection<
  "guardian.core.supported_profile", "supported_profile_state_unavailable"
> & {
  profile_name: string | null;
  version: number | null;
  surface_class: string | null;
  valid: boolean | null;
};

export type MountedRoutesSection = EvidenceSection<
  "guardian.guardian_api._refresh_supported_profile_state", "mounted_route_inventory_unavailable"
> & {
  route_families: string[] | null;
  interpretation: "mounted_only_not_authorization_health_or_release_support";
};

export type ProviderEgressSection = EvidenceSection<
  "guardian.core.config.Settings+guardian.core.egress", "provider_egress_posture_unavailable"
> & {
  configured_provider_class: string | null;
  local_only_mode: boolean | null;
  cloud_providers_allowed: boolean | null;
  egress_allowlist_configured: boolean | null;
};

export type LocalInferenceSection = EvidenceSection<
  "guardian.core.provider_registry.default_model_for_provider", "local_inference_target_unavailable"
> & {
  provider_class: "local";
  configured_target: string | null;
};

export type ConfigurationSnapshot = {
  schema_version: 1;
  generated_at: string;
  process: {
    service: "guardian";
    process_id: number;
    scope: "responding_guardian_process";
  };
  supported_profile: SupportedProfileSection;
  mounted_routes: MountedRoutesSection;
  provider_egress: ProviderEgressSection;
  local_inference: LocalInferenceSection;
};

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function section(value: unknown, owner: string, reason: string): value is Record<string, unknown> {
  return record(value) && value.owner === owner &&
    typeof value.evidence === "string" && ["declared", "resolved", "observed", "unavailable"].includes(value.evidence) &&
    (value.unavailable_reason === null || value.unavailable_reason === reason) &&
    (value.evidence !== "unavailable" || value.unavailable_reason === reason);
}

function nullableString(value: unknown, maxLength: number): boolean {
  return value === null || (typeof value === "string" && value.length > 0 && value.length <= maxLength);
}

function nullableBoolean(value: unknown): boolean {
  return value === null || typeof value === "boolean";
}

/** Validate the wire shape only. Never resolve, infer, or repair configuration. */
export function isConfigurationSnapshot(value: unknown): value is ConfigurationSnapshot {
  if (!record(value) || value.schema_version !== 1 ||
      typeof value.generated_at !== "string" || !Number.isFinite(Date.parse(value.generated_at)) ||
      !record(value.process) || value.process.service !== "guardian" ||
      value.process.scope !== "responding_guardian_process" ||
      typeof value.process.process_id !== "number" ||
      !Number.isInteger(value.process.process_id) || value.process.process_id <= 0) return false;

  const profile = value.supported_profile;
  const routes = value.mounted_routes;
  const provider = value.provider_egress;
  const local = value.local_inference;
  return section(profile, "guardian.core.supported_profile", "supported_profile_state_unavailable") &&
    nullableString(profile.profile_name, 128) && nullableString(profile.surface_class, 128) &&
    (profile.version === null || (typeof profile.version === "number" && Number.isInteger(profile.version))) &&
    nullableBoolean(profile.valid) &&
    section(routes, "guardian.guardian_api._refresh_supported_profile_state", "mounted_route_inventory_unavailable") &&
    routes.interpretation === "mounted_only_not_authorization_health_or_release_support" &&
    (routes.route_families === null || (Array.isArray(routes.route_families) && routes.route_families.length <= 128 &&
      routes.route_families.every((label: unknown) => typeof label === "string" && /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(label)))) &&
    section(provider, "guardian.core.config.Settings+guardian.core.egress", "provider_egress_posture_unavailable") &&
    nullableString(provider.configured_provider_class, 40) &&
    nullableBoolean(provider.local_only_mode) && nullableBoolean(provider.cloud_providers_allowed) &&
    nullableBoolean(provider.egress_allowlist_configured) &&
    section(local, "guardian.core.provider_registry.default_model_for_provider", "local_inference_target_unavailable") &&
    local.provider_class === "local" && nullableString(local.configured_target, 180);
}
