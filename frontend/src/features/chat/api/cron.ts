import api from "@/lib/api";

export type GuardianCronJobType = "noop" | "webhook";

export type GuardianCronJobPayload = Record<string, unknown>;

export type CreateGuardianCronJobInput = {
  isEnabled: boolean;
  jobType: GuardianCronJobType;
  name: string;
  payload: GuardianCronJobPayload;
  schedule: string;
};

export type GuardianCronJob = {
  createdAt: string | null;
  id: number;
  isEnabled: boolean;
  jobType: GuardianCronJobType | string;
  name: string;
  payload: GuardianCronJobPayload;
  schedule: string;
  updatedAt: string | null;
};

type GuardianCronJobResponse = {
  created_at?: string | null;
  id: number;
  is_enabled: boolean;
  job_type: GuardianCronJobType | string;
  name: string;
  payload?: GuardianCronJobPayload | null;
  schedule: string;
  updated_at?: string | null;
};

export const SUPPORTED_GUARDIAN_CRON_PRESETS = [
  "@hourly",
  "@daily",
  "@weekly",
  "@monthly",
] as const;

export const GUARDIAN_CRON_CUSTOM_SCHEDULE = "custom";

export type GuardianCronSchedulePreset =
  | (typeof SUPPORTED_GUARDIAN_CRON_PRESETS)[number]
  | typeof GUARDIAN_CRON_CUSTOM_SCHEDULE;

function normalizeGuardianCronJob(
  job: GuardianCronJobResponse
): GuardianCronJob {
  return {
    createdAt:
      typeof job.created_at === "string" ? job.created_at : null,
    id: Number(job.id),
    isEnabled: Boolean(job.is_enabled),
    jobType: job.job_type,
    name: String(job.name ?? ""),
    payload:
      job.payload && typeof job.payload === "object" ? job.payload : {},
    schedule: String(job.schedule ?? ""),
    updatedAt:
      typeof job.updated_at === "string" ? job.updated_at : null,
  };
}

export async function createGuardianCronJob(
  input: CreateGuardianCronJobInput
): Promise<GuardianCronJob> {
  const response = await api.post<GuardianCronJobResponse>("/api/cron/jobs", {
    is_enabled: input.isEnabled,
    job_type: input.jobType,
    name: input.name,
    payload: input.payload,
    schedule: input.schedule,
  });

  return normalizeGuardianCronJob(response.data);
}
