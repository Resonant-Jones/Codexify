

/**
 * ConnectorConfigModal
 * Multi-step wizard to configure a connector with optional OAuth (PKCE),
 * API key/local fields, test, and finish. Uses backend metadata to render fields.
 */
import React, { useEffect, useMemo, useState } from "react";
import { Connector, ConnectorOption, RequiredField } from "./useConnectors";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { Loader2 } from "lucide-react";

interface Props {
  connector: Connector;
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<Connector>) => void;
}

export const ConnectorConfigModal: React.FC<Props> = ({ connector, open, onClose, onSave }) => {
  // Local state for stepper
  const [step, setStep] = useState(0); // 0 Method, 1 Fields, 2 Authorize/Save, 3 Test, 4 Finish
  const [method, setMethod] = useState<"oauth" | "api_key" | "local" | null>(null);
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
    // Require all listed fields present
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
        const res = await api.post(`/connectors/${connector.id}/authorize`, { redirectUri });
        if (res?.data?.authUrl) {
          const w = window.open(res.data.authUrl, "oauth", "width=600,height=700");
          // Poll until connected or timeout
          const started = Date.now();
          const poll = async () => {
            try {
              const s = await api.get(`/connectors/${connector.id}`);
              if ((s.data as any)?.status === "connected") {
                setLoading(false);
                setMessage("Authorized successfully.");
                try { w && w.close(); } catch {}
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
        // API key / local: POST config fields
        const resp = await api.post(`/connectors/${connector.id}/config`, { fields });
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
      setMessage(r?.data?.ok ? "✅ Connection OK" : `❌ ${r?.data?.message || "Failed"}`);
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
      if (r?.data?.ok && r?.data?.job_id) setMessage(`Sync started (job: ${r.data.job_id})`);
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
          <Button variant={method === "oauth" ? "default" : "ghost"} className="rounded-xl" onClick={() => setMethod("oauth")}>OAuth</Button>
        )}
        {details?.capabilities?.supportsApiKey && (
          <Button variant={method === "api_key" ? "default" : "ghost"} className="rounded-xl" onClick={() => setMethod("api_key")}>API Key</Button>
        )}
        {details?.capabilities?.supportsLocal && (
          <Button variant={method === "local" ? "default" : "ghost"} className="rounded-xl" onClick={() => setMethod("local")}>Local</Button>
        )}
      </div>
      {details?.needsAdminSecret && (
        <div className="text-xs text-amber-600">This connector requires an admin secret (e.g., client secret) to be set.</div>
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
              onChange={(e) => setFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
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
        <div className="text-sm opacity-80">Click Next to open the provider and authorize access.</div>
      ) : (
        <div className="text-sm opacity-80">Click Next to save your settings.</div>
      )}
      {message && <div className="text-xs">{message}</div>}
      {loading && (
        <div className="flex items-center gap-2 text-sm opacity-80"><Loader2 className="h-4 w-4 animate-spin" /> Working…</div>
      )}
    </div>
  );

  const TestStep = (
    <div className="space-y-3">
      <div className="text-sm">Run a quick connection test.</div>
      <div className="flex items-center gap-2">
        <Button className="rounded-xl" size="sm" onClick={handleTest} disabled={loading}>
          Test connection
        </Button>
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      </div>
      {message && <div className="text-xs">{message}</div>}
    </div>
  );

  const FinishStep = (
    <div className="space-y-3">
      <div className="text-sm">{connector.status === "connected" ? "Connected" : "Configured"}</div>
      <div className="flex items-center gap-2">
        <Button className="rounded-xl" size="sm" onClick={handleSync} disabled={loading}>
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
    if (step === 2) return !loading; // allow Next after action initiates
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
      // Kick off authorize/save when moving from step 2
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" role="dialog" aria-modal="true" aria-label={`${connector.name} setup`}>
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-2xl p-6 space-y-4">
        {StepHeader}
        {/* Step indicator */}
        <div className="text-xs opacity-70">Method · Fields · Authorize/Save · Test · Finish</div>
        {/* Step content */}
        {step === 0 && MethodStep}
        {step === 1 && FieldsStep}
        {step === 2 && AuthorizeOrSaveStep}
        {step === 3 && TestStep}
        {step === 4 && FinishStep}
        <div className="flex justify-between pt-2">
          <div className="flex gap-2">
            <Button variant="ghost" className="rounded-xl" onClick={close}>Cancel</Button>
            <Button variant="ghost" className="rounded-xl" onClick={back} disabled={step === 0}>Back</Button>
          </div>
          <Button className="rounded-xl" onClick={next} disabled={!canNext}>
            {step < 4 ? "Next" : "Done"}
          </Button>
        </div>
      </div>
    </div>
  );
};
