

import React, { useState } from "react";
import { Connector } from "./useConnectors";
import api from "@/lib/api";
import { useConnectors } from "./useConnectors";
import { ConnectorConfigModal } from "./ConnectorConfigModal";
import { Button } from "@/components/ui/button";

interface Props {
  connector: Connector;
  onUpdate: (id: string, data: Partial<Connector>) => void;
}

export const ConnectorCard: React.FC<Props> = ({ connector, onUpdate }) => {
  const [open, setOpen] = useState(false);
  const { authorizeOAuth, testConnector, syncConnector, refresh } = useConnectors();
  const canOAuth = connector.capabilities?.supportsOAuth;
  async function onTest() {
    const r = await testConnector(connector.id);
    alert(r?.ok ? "Connection OK" : `Test failed: ${r?.message || "Unknown"}`);
  }
  async function onSync() {
    const r = await syncConnector(connector.id);
    if (r?.job_id) alert(`Sync queued: ${r.job_id}`);
  }

  return (
    <div className="border border-[color:var(--panel-border)] rounded-xl p-4 flex justify-between items-center gap-4">
      <div className="min-w-0">
        <div className="font-semibold">{connector.name}</div>
        <div
          className={`text-xs capitalize ${
            connector.status === "connected" ? "text-green-600" : "text-red-500"
          }`}
        >
          {connector.status}
        </div>
      </div>
      <div className="flex items-center gap-2 ml-auto">
        {canOAuth && connector.status !== "connected" && (
          <Button type="button" size="sm" className="rounded-xl" onClick={() => authorizeOAuth(connector.id)}>
            Connect
          </Button>
        )}
        {connector.status === "connected" && (
          <>
            <Button type="button" size="sm" className="rounded-xl" onClick={onTest}>
              Test
            </Button>
            <Button type="button" size="sm" className="rounded-xl" onClick={onSync}>
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
