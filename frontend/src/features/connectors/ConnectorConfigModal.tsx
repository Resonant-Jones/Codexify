import React, { useEffect, useMemo, useState } from "react";
import { Connector, RequiredField } from "./useConnectors";
import {
  AUTH_METHOD_LABELS,
  AuthMethod,
  canLaunchOAuth,
  canLaunchSetup,
  ConnectionEntry,
  IMPLEMENTATION_STATE_LABELS,
  SETUP_STATE_LABELS,
} from "./connectionCatalog";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { Loader2 } from "lucide-react";

interface LegacyProps {
  connector: Connector;
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<Connector>) => void;
}

/**
 * Legacy connector setup wizard (GitHub sync connector and other
 * ``/api/connectors`` entries). Behavior is preserved unchanged; it remains
 * reachable from the legacy connectors section of the Settings bay.
 */
export const ConnectorConfigModal: React.FC<LegacyProps> = ({
  connector,
  open,
  onClose,
  onSave,
}) => {
  // Local state for stepper
  const [step, setStep] = useState(0); // 0 Method, 1 Fields, 2 Authorize/Save, 3 Test, 4 Finish
  const [method, setMethod] = useState<"oauth" | "api_key" | "local" | null>(
    null
  );
  const [fields, setFields] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [details, setDetails] = useState<Connector | null>(null);

  // Fetch full connector info (with masked config) on open
  useEffect(() => {
    if (!open) return;
    setStep(0);
    setMessage(null);
    api
      .get<Connector>(`/connectors/${connector.id}`)
      .then((res) => {
        setDetails(res.data as any);
        // Default method if only one capability
        const caps = res.data?.capabilities || connector.capabilities;
        if (caps) {
          const available = [
            caps.supportsOAuth ? "oauth" : null,
            caps.supportsApiKey ? "api_key" : null,
            caps.supportsLocal ? "local" : null,
          ].filter(Boolean) as ("oauth" | "api_key" | "local")[];
          if (available.length === 1) setMethod(available[0]);
        }
      })
      .catch(() => setDetails(connector));
  }, [open, connector.id]);

  const requiredFields: RequiredField[] = useMemo(() => {
    return (details?.requiredFields || connector.requiredFields || []) as any;
  }, [details, connector]);

  const canNextFields = useMemo(() => {
    if (!requiredFields || requiredFields.length === 0) return true;
    return requiredFields.every((f) => {
      const v = fields[f.key];
      return typeof v === "string" && v.trim().length > 0;
    });
  }, [fields, requiredFields]);

  if (!open) return null;

  function close() {
    setStep(0);
    setMethod(null);
    setFields({});
    setMessage(null);
    onClose();
  }

  async function handleAuthorizeOrSave() {
    setLoading(true);
    setMessage(null);
    try {
      if (method === "oauth") {
        const redirectUri = window.location.origin + "/auth/callback";
        const res = await api.post(`/connectors/${connector.id}/authorize`, {
          redirectUri,
        });
        if (res?.data?.authUrl) {
          const w = window.open(res.data.authUrl, "oauth", "width=600,height=700");
          const started = Date.now();
          const poll = async () => {
            try {
              const s = await api.get(`/connectors/${connector.id}`);
              if ((s.data as any)?.status === "connected") {
                setLoading(false);
                setMessage("Authorized successfully.");
                try {
                  w && w.close();
                } catch {}
                setStep(3);
                return;
              }
            } catch {}
            if (Date.now() - started < 60000) setTimeout(poll, 1500);
            else {
              setLoading(false);
              setMessage("Authorization timed out.");
            }
          };
          setTimeout(poll, 1500);
          return;
        }
      } else {
        const resp = await api.post(`/connectors/${connector.id}/config`, {
          fields,
        });
        if (resp?.data?.ok) {
          setMessage("Settings saved.");
          setStep(3);
        } else {
          setMessage(resp?.data?.error || "Save failed");
        }
      }
    } catch (e: any) {
      setMessage(e?.response?.data?.error || e?.message || "Operation failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleTest() {
    setLoading(true);
    setMessage(null);
    try {
      const r = await api.post(`/connectors/${connector.id}/test`);
      setMessage(
        r?.data?.ok ? "✅ Connection OK" : `❌ ${r?.data?.message || "Failed"}`
      );
    } catch (e: any) {
      setMessage(`❌ ${e?.response?.data?.error || e?.message || "Failed"}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleSync() {
    setLoading(true);
    setMessage(null);
    try {
      const r = await api.post(`/connectors/${connector.id}/sync`);
      if (r?.data?.ok && r?.data?.job_id)
        setMessage(`Sync started (job: ${r.data.job_id})`);
      else setMessage("Failed to start sync");
    } catch (e: any) {
      setMessage(`❌ ${e?.response?.data?.error || e?.message || "Failed"}`);
    } finally {
      setLoading(false);
    }
  }

  // Step content renderers
  const StepHeader = (
    <div className="flex items-center justify-between">
      <div className="text-lg font-semibold">{connector.name} Setup</div>
      <div className="text-xs opacity-70">Step {step + 1} of 5</div>
    </div>
  );

  const MethodStep = (
    <div className="space-y-3">
      <div className="text-sm font-medium">Choose method</div>
      <div className="flex gap-2">
        {details?.capabilities?.supportsOAuth && (
          <Button
            variant={method === "oauth" ? "default" : "ghost"}
            className="rounded-xl"
            onClick={() => setMethod("oauth")}
          >
            OAuth
          </Button>
        )}
        {details?.capabilities?.supportsApiKey && (
          <Button
            variant={method === "api_key" ? "default" : "ghost"}
            className="rounded-xl"
            onClick={() => setMethod("api_key")}
          >
            API Key
          </Button>
        )}
        {details?.capabilities?.supportsLocal && (
          <Button
            variant={method === "local" ? "default" : "ghost"}
            className="rounded-xl"
            onClick={() => setMethod("local")}
          >
            Local
          </Button>
        )}
      </div>
      {details?.needsAdminSecret && (
        <div className="text-xs text-amber-600">
          This connector requires an admin secret (e.g., client secret) to be
          set.
        </div>
      )}
    </div>
  );

  const FieldsStep = (
    <div className="space-y-3">
      {requiredFields && requiredFields.length > 0 ? (
        requiredFields.map((f) => (
          <div key={f.key} className="flex flex-col">
            <label className="text-sm font-medium mb-1">{f.label}</label>
            <input
              type={f.secret ? "password" : "text"}
              value={fields[f.key] || ""}
              onChange={(e) =>
                setFields((prev) => ({ ...prev, [f.key]: e.target.value }))
              }
              className="border rounded px-2 py-1"
              placeholder={f.secret ? "••••" : ""}
            />
          </div>
        ))
      ) : (
        <div className="text-sm opacity-70">No fields required.</div>
      )}
    </div>
  );

  const AuthorizeOrSaveStep = (
    <div className="space-y-3">
      {method === "oauth" ? (
        <div className="text-sm opacity-80">
          Click Next to open the provider and authorize access.
        </div>
      ) : (
        <div className="text-sm opacity-80">
          Click Next to save your settings.
        </div>
      )}
      {message && <div className="text-xs">{message}</div>}
      {loading && (
        <div className="flex items-center gap-2 text-sm opacity-80">
          <Loader2 className="h-4 w-4 animate-spin" /> Working…
        </div>
      )}
    </div>
  );

  const TestStep = (
    <div className="space-y-3">
      <div className="text-sm">Run a quick connection test.</div>
      <div className="flex items-center gap-2">
        <Button
          className="rounded-xl"
          size="sm"
          onClick={handleTest}
          disabled={loading}
        >
          Test connection
        </Button>
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      </div>
      {message && <div className="text-xs">{message}</div>}
    </div>
  );

  const FinishStep = (
    <div className="space-y-3">
      <div className="text-sm">
        {connector.status === "connected" ? "Connected" : "Configured"}
      </div>
      <div className="flex items-center gap-2">
        <Button
          className="rounded-xl"
          size="sm"
          onClick={handleSync}
          disabled={loading}
        >
          Sync now
        </Button>
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      </div>
      {message && <div className="text-xs">{message}</div>}
    </div>
  );

  // Controls
  const canNext = useMemo(() => {
    if (step === 0) return !!method;
    if (step === 1) return canNextFields;
    if (step === 2) return !loading;
    if (step === 3) return true;
    return true;
  }, [step, method, canNextFields, loading]);

  function next() {
    if (step === 0 && method) {
      setStep(1);
      return;
    }
    if (step === 1) {
      setStep(2);
      return;
    }
    if (step === 2) {
      handleAuthorizeOrSave();
      return;
    }
    if (step === 3) {
      setStep(4);
      return;
    }
    if (step === 4) {
      onSave({ options: connector.options });
      close();
      return;
    }
  }

  function back() {
    setMessage(null);
    setStep((s) => Math.max(0, s - 1));
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      role="dialog"
      aria-modal="true"
      aria-label={`${connector.name} setup`}
    >
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-2xl p-6 space-y-4">
        {StepHeader}
        <div className="text-xs opacity-70">
          Method · Fields · Authorize/Save · Test · Finish
        </div>
        {step === 0 && MethodStep}
        {step === 1 && FieldsStep}
        {step === 2 && AuthorizeOrSaveStep}
        {step === 3 && TestStep}
        {step === 4 && FinishStep}
        <div className="flex justify-between pt-2">
          <div className="flex gap-2">
            <Button variant="ghost" className="rounded-xl" onClick={close}>
              Cancel
            </Button>
            <Button
              variant="ghost"
              className="rounded-xl"
              onClick={back}
              disabled={step === 0}
            >
              Back
            </Button>
          </div>
          <Button className="rounded-xl" onClick={next} disabled={!canNext}>
            {step < 4 ? "Next" : "Done"}
          </Button>
        </div>
      </div>
    </div>
  );
};

interface ConnectionProps {
  connection: ConnectionEntry;
  open: boolean;
  onClose: () => void;
  onChanged: () => void;
}

type WizardStep = "overview" | "method" | "fields" | "save" | "done";

function eligibleAuthMethods(entry: ConnectionEntry): AuthMethod[] {
  return entry.auth_methods.filter((method) => {
    if (method === "oauth_browser" || method === "oauth_device") {
      return canLaunchOAuth(entry);
    }
    if (method === "none") return true;
    // api_key / token / service_credentials / local_endpoint need a real
    // backing mutation route to save against.
    return canLaunchSetup(entry);
  });
}

function buildSetupSteps(entry: ConnectionEntry): WizardStep[] {
  const steps: WizardStep[] = ["overview"];
  if (eligibleAuthMethods(entry).length > 1) steps.push("method");
  if (entry.required_fields.length > 0 && canLaunchSetup(entry)) {
    steps.push("fields");
  }
  if (canLaunchSetup(entry)) steps.push("save");
  steps.push("done");
  return steps;
}

/**
 * Metadata-driven setup wizard for canonical Connections catalog entries.
 *
 * The wizard renders only what the entry's catalog metadata allows:
 * method choices come from ``auth_methods``, fields from ``required_fields``,
 * and the save action only exists when the entry has a real backing route.
 * OAuth actions are only ever enabled when a backend authorization handler
 * exists; entries without one visibly say setup is not yet available instead
 * of opening a dead flow.
 */
export const ConnectionConfigModal: React.FC<ConnectionProps> = ({
  connection,
  open,
  onClose,
  onChanged,
}) => {
  const [stepIndex, setStepIndex] = useState(0);
  const [method, setMethod] = useState<AuthMethod | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [saveSucceeded, setSaveSucceeded] = useState(false);

  const steps = useMemo(() => buildSetupSteps(connection), [connection]);
  const step = steps[Math.min(stepIndex, steps.length - 1)];
  const methods = useMemo(() => eligibleAuthMethods(connection), [connection]);

  useEffect(() => {
    if (!open) return;
    setStepIndex(0);
    setMethod(null);
    setFields({});
    setMessage(null);
    setSaveSucceeded(false);
  }, [open, connection.id]);

  if (!open) return null;

  const setupUnavailable =
    connection.implementation_state === "unimplemented" ||
    !canLaunchSetup(connection);

  function close() {
    setStepIndex(0);
    setMethod(null);
    setFields({});
    setMessage(null);
    setSaveSucceeded(false);
    onClose();
  }

  function effectiveMethod(): AuthMethod {
    if (method) return method;
    if (methods.length === 1) return methods[0];
    return methods[0] ?? ("none" as AuthMethod);
  }

  async function handleSave() {
    setLoading(true);
    setMessage(null);
    setSaveSucceeded(false);
    try {
      const route = connection.runtime_binding.setup_route;
      if (!route) {
        setMessage("Setup is not yet available for this connection.");
        return;
      }
      let body: Record<string, unknown>;
      if (route === "/api/channels/configs") {
        body = { channel: connection.id, config_json: fields };
      } else {
        body = { settings: fields };
      }
      const res = await api.post(route, body);
      if (res?.data && !res.data.error) {
        setMessage("Settings saved.");
        setSaveSucceeded(true);
        onChanged();
      } else {
        setMessage(res?.data?.error || "Save failed");
      }
    } catch (e: any) {
      setMessage(
        e?.response?.data?.detail ||
          e?.response?.data?.error ||
          e?.message ||
          "Operation failed"
      );
    } finally {
      setLoading(false);
    }
  }

  const canNextFields =
    connection.required_fields.length === 0 ||
    connection.required_fields.every((f) => {
      const v = fields[f.key];
      return typeof v === "string" && v.trim().length > 0;
    });

  function canProceed(): boolean {
    if (step === "overview") return true;
    if (step === "method") return Boolean(method);
    if (step === "fields") return canNextFields;
    if (step === "save") return !loading && saveSucceeded;
    return true;
  }

  function next() {
    const index = stepIndex + 1;
    if (index >= steps.length) {
      close();
      return;
    }
    if (steps[index] === "save") {
      handleSave();
    }
    setStepIndex(index);
  }

  function back() {
    setMessage(null);
    setStepIndex((s) => Math.max(0, s - 1));
  }

  const OverviewStep = (
    <div className="space-y-3">
      <div className="text-sm opacity-80">{connection.description}</div>
      <div className="space-y-1 text-xs" style={{ color: "var(--muted)" }}>
        <div>
          Adapter:{" "}
          <span className="font-medium">
            {IMPLEMENTATION_STATE_LABELS[connection.implementation_state]}
          </span>
        </div>
        <div>
          Setup:{" "}
          <span className="font-medium">
            {SETUP_STATE_LABELS[connection.setup_state]}
          </span>
        </div>
        {connection.capabilities.length > 0 && (
          <div>Enables: {connection.capabilities.join(", ")}</div>
        )}
        {connection.authorization && connection.authorization.registered && (
          <div>
            Provider registry:{" "}
            <span className="font-medium">
              {connection.authorization.governance_classification || "listed"}
            </span>
          </div>
        )}
        {connection.authorization && !connection.authorization.registered && (
          <div>Provider registry: not listed</div>
        )}
      </div>
      {setupUnavailable && (
        <div
          className="text-xs rounded-[var(--tile-radius,19px)] border border-[color:var(--panel-border)] p-2"
          style={{ color: "var(--danger-text)" }}
        >
          Setup is not yet available for this connection. This entry is
          catalog discovery only.
        </div>
      )}
      {connection.oauth?.connection && (
        <div
          className="text-xs rounded-[var(--tile-radius,19px)] border border-[color:var(--panel-border)] p-2"
          style={{ color: "var(--muted)" }}
        >
          Persisted OAuth state: {connection.oauth.connection.status}
          {connection.oauth.connection.expires_at
            ? ` · expires ${connection.oauth.connection.expires_at}`
            : ""}
        </div>
      )}
    </div>
  );

  const MethodStep = (
    <div className="space-y-3">
      <div className="text-sm font-medium">Choose authentication method</div>
      <div className="flex flex-wrap gap-2">
        {methods.map((candidate) => (
          <Button
            key={candidate}
            variant={method === candidate ? "default" : "ghost"}
            className="rounded-xl"
            onClick={() => setMethod(candidate)}
          >
            {AUTH_METHOD_LABELS[candidate]}
          </Button>
        ))}
      </div>
      {connection.auth_methods.some(
        (m) => m === "oauth_browser" || m === "oauth_device"
      ) &&
        !canLaunchOAuth(connection) && (
          <div className="text-xs" style={{ color: "var(--danger-text)" }}>
            OAuth setup is not yet available: no backend authorization handler
            exists for this provider.
          </div>
        )}
    </div>
  );

  const FieldsStep = (
    <div className="space-y-3">
      {connection.required_fields.map((f) => (
        <div key={f.key} className="flex flex-col">
          <label className="text-sm font-medium mb-1">{f.label}</label>
          <input
            type={f.secret ? "password" : "text"}
            value={fields[f.key] || ""}
            onChange={(e) =>
              setFields((prev) => ({ ...prev, [f.key]: e.target.value }))
            }
            className="border rounded px-2 py-1"
            placeholder={f.secret ? "••••" : ""}
          />
        </div>
      ))}
      <div className="text-xs" style={{ color: "var(--muted)" }}>
        Credentials are stored server-side; they are never returned to the
        browser.
      </div>
    </div>
  );

  const SaveStep = (
    <div className="space-y-3">
      <div className="text-sm opacity-80">
        {effectiveMethod() === "oauth_browser" ||
        effectiveMethod() === "oauth_device"
          ? "Sign in with the provider to continue."
          : "Continue to save your settings."}
      </div>
      {message && <div className="text-xs">{message}</div>}
      {loading && (
        <div className="flex items-center gap-2 text-sm opacity-80">
          <Loader2 className="h-4 w-4 animate-spin" /> Working…
        </div>
      )}
    </div>
  );

  const DoneStep = (
    <div className="space-y-3">
      <div className="text-sm">
        {connection.setup_state === "connected"
          ? "Connected"
          : "Configuration saved."}
      </div>
      {message && <div className="text-xs">{message}</div>}
    </div>
  );

  const StepLabel: Record<WizardStep, string> = {
    overview: "Overview",
    method: "Method",
    fields: "Fields",
    save: "Configure",
    done: "Done",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      role="dialog"
      aria-modal="true"
      aria-label={`${connection.display_name} setup`}
    >
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-lg font-semibold">
            {connection.display_name} Setup
          </div>
          <div className="text-xs opacity-70">
            Step {stepIndex + 1} of {steps.length}
          </div>
        </div>
        <div className="text-xs opacity-70">
          {steps.map((s) => StepLabel[s]).join(" · ")}
        </div>
        {step === "overview" && OverviewStep}
        {step === "method" && MethodStep}
        {step === "fields" && FieldsStep}
        {step === "save" && SaveStep}
        {step === "done" && DoneStep}
        <div className="flex justify-between pt-2">
          <div className="flex gap-2">
            <Button variant="ghost" className="rounded-xl" onClick={close}>
              Cancel
            </Button>
            <Button
              variant="ghost"
              className="rounded-xl"
              onClick={back}
              disabled={stepIndex === 0}
            >
              Back
            </Button>
          </div>
          <Button
            className="rounded-xl"
            onClick={next}
            disabled={!canProceed()}
          >
            {stepIndex >= steps.length - 1 ? "Done" : "Continue"}
          </Button>
        </div>
      </div>
    </div>
  );
};
