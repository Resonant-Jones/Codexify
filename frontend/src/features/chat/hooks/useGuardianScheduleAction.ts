import { useCallback, useMemo, useState } from "react";

import {
  createGuardianCronJob,
  GUARDIAN_CRON_CUSTOM_SCHEDULE,
  SUPPORTED_GUARDIAN_CRON_PRESETS,
  type CreateGuardianCronJobInput,
  type GuardianCronJob,
  type GuardianCronJobType,
  type GuardianCronSchedulePreset,
} from "@/features/chat/api/cron";

const SIMPLE_INTERVAL_RE = /^\*\/([1-9]\d*) \* \* \* \*$/;

type ValidationErrors = Partial<
  Record<"name" | "schedule" | "targetReference", string>
>;

export type GuardianScheduleFormState = {
  customSchedule: string;
  isEnabled: boolean;
  jobType: GuardianCronJobType;
  name: string;
  schedulePreset: GuardianCronSchedulePreset;
  targetReference: string;
};

export type GuardianScheduleReview = {
  input: CreateGuardianCronJobInput;
  summary: Array<{ label: string; value: string }>;
};

export type UseGuardianScheduleActionResult = {
  cancelReview: () => void;
  confirmCreation: () => Promise<boolean>;
  createdJob: GuardianCronJob | null;
  error: string | null;
  form: GuardianScheduleFormState;
  isSubmitting: boolean;
  isValid: boolean;
  review: GuardianScheduleReview | null;
  setField: <K extends keyof GuardianScheduleFormState>(
    field: K,
    value: GuardianScheduleFormState[K]
  ) => void;
  submit: () => Promise<boolean>;
  validationErrors: ValidationErrors;
};

function getErrorMessage(error: unknown): string {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const response = error.response as { data?: { detail?: unknown; error?: unknown } };
    if (typeof response.data?.detail === "string" && response.data.detail.trim()) {
      return response.data.detail;
    }
    if (typeof response.data?.error === "string" && response.data.error.trim()) {
      return response.data.error;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Failed to create scheduled job.";
}

function isValidSchedule(schedule: string): boolean {
  return (
    SUPPORTED_GUARDIAN_CRON_PRESETS.includes(
      schedule as (typeof SUPPORTED_GUARDIAN_CRON_PRESETS)[number]
    ) || SIMPLE_INTERVAL_RE.test(schedule)
  );
}

function buildRequest(
  form: GuardianScheduleFormState
): CreateGuardianCronJobInput {
  const reference = form.targetReference.trim();

  return {
    isEnabled: form.isEnabled,
    jobType: form.jobType,
    name: form.name.trim(),
    payload:
      form.jobType === "webhook"
        ? { url: reference }
        : { reference },
    schedule:
      form.schedulePreset === GUARDIAN_CRON_CUSTOM_SCHEDULE
        ? form.customSchedule.trim()
        : form.schedulePreset,
  };
}

function validateForm(form: GuardianScheduleFormState): ValidationErrors {
  const errors: ValidationErrors = {};

  if (!form.name.trim()) {
    errors.name = "Job name is required.";
  }

  const targetReference = form.targetReference.trim();
  if (!targetReference) {
    errors.targetReference =
      form.jobType === "webhook"
        ? "Webhook URL is required."
        : "Payload reference is required.";
  } else if (
    form.jobType === "webhook" &&
    !/^https?:\/\/\S+$/i.test(targetReference)
  ) {
    errors.targetReference =
      "Webhook URL must begin with http:// or https://.";
  }

  const schedule =
    form.schedulePreset === GUARDIAN_CRON_CUSTOM_SCHEDULE
      ? form.customSchedule.trim()
      : form.schedulePreset;
  if (!schedule) {
    errors.schedule = "Schedule is required.";
  } else if (!isValidSchedule(schedule)) {
    errors.schedule =
      "Use @hourly, @daily, @weekly, @monthly, or */N * * * *.";
  }

  return errors;
}

function buildReview(
  form: GuardianScheduleFormState
): GuardianScheduleReview {
  const input = buildRequest(form);
  const summary = [
    { label: "Name", value: input.name },
    { label: "Schedule", value: input.schedule },
    {
      label: "Job type",
      value: input.jobType === "webhook" ? "Webhook" : "No-op",
    },
    {
      label: input.jobType === "webhook" ? "Webhook URL" : "Payload reference",
      value:
        input.jobType === "webhook"
          ? String(input.payload.url ?? "")
          : String(input.payload.reference ?? ""),
    },
    {
      label: "Enabled on create",
      value: input.isEnabled ? "Yes" : "No",
    },
  ];

  return { input, summary };
}

export function useGuardianScheduleAction(): UseGuardianScheduleActionResult {
  const [form, setForm] = useState<GuardianScheduleFormState>({
    customSchedule: "",
    isEnabled: true,
    jobType: "noop",
    name: "",
    schedulePreset: "@daily",
    targetReference: "",
  });
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>(
    {}
  );
  const [review, setReview] = useState<GuardianScheduleReview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createdJob, setCreatedJob] = useState<GuardianCronJob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const setField = useCallback(
    <K extends keyof GuardianScheduleFormState>(
      field: K,
      value: GuardianScheduleFormState[K]
    ) => {
      setForm((current) => {
        const next = { ...current, [field]: value };
        if (field === "jobType") {
          next.targetReference = "";
        }
        return next;
      });
      setValidationErrors((current) => {
        if (!current[field]) return current;
        const next = { ...current };
        delete next[field];
        return next;
      });
      setError(null);
      setCreatedJob(null);
      setReview(null);
    },
    []
  );

  const cancelReview = useCallback(() => {
    setReview(null);
    setError(null);
  }, []);

  const confirmCreation = useCallback(async () => {
    const nextErrors = validateForm(form);
    setValidationErrors(nextErrors);
    setError(null);
    setCreatedJob(null);

    if (Object.keys(nextErrors).length > 0) {
      setReview(null);
      return false;
    }

    setReview(buildReview(form));
    return true;
  }, [form]);

  const submit = useCallback(async () => {
    if (!review) {
      const confirmed = await confirmCreation();
      if (!confirmed) return false;
      return false;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const created = await createGuardianCronJob(review.input);
      setCreatedJob(created);
      setReview(null);
      return true;
    } catch (nextError) {
      setError(getErrorMessage(nextError));
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, [confirmCreation, review]);

  const isValid = useMemo(
    () => Object.keys(validateForm(form)).length === 0,
    [form]
  );

  return {
    cancelReview,
    confirmCreation,
    createdJob,
    error,
    form,
    isSubmitting,
    isValid,
    review,
    setField,
    submit,
    validationErrors,
  };
}

export default useGuardianScheduleAction;
