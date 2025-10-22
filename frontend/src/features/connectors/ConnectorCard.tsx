import React, { useState } from "react";
import { Connector } from "./useConnectors";
import { ConnectorConfigModal } from "./ConnectorConfigModal";
import { Button } from "@/components/ui/button";
import { getConnectorLogo } from "./connectorLogos";

interface Props {
  connector: Connector;
  onUpdate: (id: string, data: Partial<Connector>) => void;
  onAuthorize: (id: string) => Promise<void> | void;
  onTest: (id: string) => Promise<{ ok?: boolean; message?: string } | undefined>;
  onSync: (id: string) => Promise<{ job_id?: number } | null>;
}

export const ConnectorCard: React.FC<Props> = ({ connector, onUpdate, onAuthorize, onTest, onSync }) => {
  const [open, setOpen] = useState(false);
  const canOAuth = connector.capabilities?.supportsOAuth;
  const logo = getConnectorLogo(connector.type, connector.id);
  const statusColor = connector.status === "connected" ? "text-emerald-500" : connector.status === "disconnected" ? "text-red-500" : "text-gray-400";
  let lastSyncLabel: string | null = null;
  if (connector.lastSyncAt) {
    const parsed = new Date(connector.lastSyncAt);
    if (!Number.isNaN(parsed.getTime())) {
      lastSyncLabel = parsed.toLocaleString();
    }
  }

  async function handleTest() {
    const r = await onTest(connector.id);
    alert(r?.ok ? "Connection OK" : `Test failed: ${r?.message || "Unknown"}`);
  }
  async function handleSync() {
    const r = await onSync(connector.id);
    if (r?.job_id) alert(`Sync queued: ${r.job_id}`);
  }

  return (
    <div className="border border-[color:var(--panel-border)] rounded-xl p-4 flex items-center gap-4" style={{ background: "var(--panel-bg)", color: "var(--text)" }}>
      <div className="flex items-center gap-3 min-w-0">
        {logo ? (
          <img src={logo} alt={`${connector.name} logo`} className="h-8 w-8 shrink-0" />
        ) : (
          <div className="h-8 w-8 shrink-0 rounded-full border border-[color:var(--panel-border)] flex items-center justify-center text-sm font-semibold" style={{ background: "var(--panel-bg)" }}>
            {connector.name?.charAt(0)?.toUpperCase() || "?"}
          </div>
        )}
        <div className="min-w-0">
          <div className="font-semibold leading-tight truncate">{connector.name}</div>
          <div className={`text-xs capitalize ${statusColor}`}>{connector.status}</div>
          {lastSyncLabel && (
            <div className="text-[11px] opacity-60">Last sync: {lastSyncLabel}</div>
          )}
          {connector.errorMessage && (
            <div className="text-[11px] text-amber-400 truncate">{connector.errorMessage}</div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 ml-auto">
        {canOAuth && connector.status !== "connected" && (
          <Button type="button" size="sm" className="rounded-xl" onClick={() => onAuthorize(connector.id)}>
            Connect
          </Button>
        )}
        {connector.status === "connected" && (
          <>
            <Button type="button" size="sm" className="rounded-xl" onClick={handleTest}>
              Test
            </Button>
            <Button type="button" size="sm" className="rounded-xl" onClick={handleSync}>
              Sync now
            </Button>
          </>
        )}
        <Button type="button" size="sm" className="rounded-xl" onClick={() => setOpen(true)}>
          Configure
        </Button>
      </div>
      <ConnectorConfigModal
        connector={connector}
        open={open}
        onClose={() => setOpen(false)}
        onSave={(data) => onUpdate(connector.id, data)}
      />
    </div>
  );
};
