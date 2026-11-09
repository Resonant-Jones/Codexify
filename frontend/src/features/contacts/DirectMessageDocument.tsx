import { useState } from "react";

import { downloadAsset } from "@/lib/assetActions";
import {
  revokeSharedDocument,
  sharedDocumentDownloadUrl,
  type DirectMessageEnvelope,
} from "@/lib/direct-messages";

export default function DirectMessageDocument({ message }: { message: DirectMessageEnvelope }) {
  const attachment = message.document_attachment;
  const [revoked, setRevoked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!attachment?.available || revoked) {
    return (
      <p className="people-message-body">
        {revoked ? "Access revoked." : "Shared document unavailable."}
      </p>
    );
  }

  const act = async (action: "download" | "revoke") => {
    setBusy(true);
    setError("");
    try {
      if (action === "revoke") {
        await revokeSharedDocument(message);
        setRevoked(true);
      } else {
        await downloadAsset({
          url: sharedDocumentDownloadUrl(message),
          filename: attachment.filename ?? undefined,
        });
      }
    } catch {
      setError(action === "revoke" ? "Could not revoke access." : "Could not download the shared document.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="people-message-body">
      <button type="button" disabled={busy} onClick={() => void act("download")}>
        Download {attachment.filename ?? "document"}
      </button>
      {attachment.can_revoke ? (
        <button type="button" disabled={busy} onClick={() => void act("revoke")}>
          Revoke access
        </button>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
    </div>
  );
}
