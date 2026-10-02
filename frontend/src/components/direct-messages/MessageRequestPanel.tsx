import { useCallback, useEffect, useState } from "react";

import {
  archiveMessageRequest,
  claimSocialIdentityUsername,
  fetchMessageRequests,
  fetchMessageRequestHistoryPreference,
  fetchOwnSocialIdentity,
  normalizeDirectMessageError,
  peerPresentationLabel,
  sendMessageRequest,
  setMessageRequestHistoryPreference,
  transitionMessageRequest,
  type DirectMessageRequest,
  type DirectMessageSocialProfile,
} from "@/lib/direct-messages";

type Props = {
  introPeer: DirectMessageSocialProfile | null;
  onIntroClose: () => void;
  onIdentity: (profile: DirectMessageSocialProfile) => void;
  onAccepted: (conversationId: string) => Promise<void>;
};

export default function MessageRequestPanel({
  introPeer,
  onIntroClose,
  onIdentity,
  onAccepted,
}: Props) {
  const [profile, setProfile] = useState<DirectMessageSocialProfile | null>(
    null,
  );
  const [requests, setRequests] = useState<DirectMessageRequest[]>([]);
  const [history, setHistory] = useState(false);
  const [autoHide, setAutoHide] = useState(false);
  const [username, setUsername] = useState("");
  const [note, setNote] = useState("");
  const [attemptKey, setAttemptKey] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const [identity, rows, preference] = await Promise.all([
      fetchOwnSocialIdentity(),
      fetchMessageRequests(history),
      fetchMessageRequestHistoryPreference(),
    ]);
    setProfile(identity);
    onIdentity(identity);
    setRequests(rows);
    setAutoHide(preference);
  }, [history, onIdentity]);

  useEffect(() => {
    let active = true;
    void reload().catch((failure) => {
      if (active) setError(normalizeDirectMessageError(failure).message);
    });
    return () => {
      active = false;
    };
  }, [reload]);

  useEffect(() => {
    setNote("");
    setAttemptKey(crypto.randomUUID());
    setError(null);
  }, [introPeer?.profile_id]);

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (failure) {
      setError(normalizeDirectMessageError(failure).message);
    } finally {
      setBusy(false);
    }
  };

  const changeRequest = (
    request: DirectMessageRequest,
    action: "accept" | "decline" | "withdraw",
  ) =>
    run(async () => {
      const result = await transitionMessageRequest(request.request_id, action);
      if (result.conversation_id) await onAccepted(result.conversation_id);
    });

  return (
    <section
      className="mx-4 mb-3 space-y-3 rounded-xl border border-[var(--panel-border)] p-3"
      aria-label="Message requests"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold">Message requests</h4>
        <button
          type="button"
          disabled={busy}
          onClick={() => void run(async () => {})}
        >
          Refresh requests
        </button>
      </div>
      <p className="text-xs text-[var(--text-subtle)]">
        Open or refresh People to see new requests. Pending requests expire
        after 30 days.
      </p>
      {profile?.username_state === "unset" ? (
        <form
          aria-label="Choose messaging username"
          onSubmit={(event) => {
            event.preventDefault();
            void run(async () => {
              const identity = await claimSocialIdentityUsername(username);
              setProfile(identity);
              onIdentity(identity);
            });
          }}
        >
          <p className="text-sm">
            Choose a username to find People and send requests.
          </p>
          <input
            aria-label="Messaging username"
            value={username}
            maxLength={32}
            onChange={(event) => setUsername(event.target.value)}
          />
          <button type="submit" disabled={busy || !username.trim()}>
            Claim username
          </button>
        </form>
      ) : profile ? (
        <p className="text-xs">Your username: @{profile.username}</p>
      ) : null}
      {introPeer ? (
        <form
          aria-label="Introductory message request"
          onSubmit={(event) => {
            event.preventDefault();
            void run(async () => {
              const result = await sendMessageRequest(
                introPeer,
                note,
                attemptKey,
              );
              onIntroClose();
              if (result.conversation_id)
                await onAccepted(result.conversation_id);
            });
          }}
          className="space-y-2"
        >
          <p className="text-sm">
            Send a message request to {peerPresentationLabel(introPeer)}
          </p>
          <textarea
            aria-label="Introductory note"
            maxLength={32000}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className="w-full rounded border border-[var(--panel-border)] bg-[var(--panel-bg)] p-2"
          />
          <p className="text-xs text-[var(--text-subtle)]">
            They must accept before an ordinary conversation starts.
          </p>
          <button type="submit" disabled={busy || !note.trim()}>
            Send request
          </button>
          <button type="button" disabled={busy} onClick={onIntroClose}>
            Cancel request
          </button>
        </form>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy}
          aria-pressed={history}
          onClick={() => setHistory((value) => !value)}
        >
          {history ? "Show pending requests" : "Request history"}
        </button>
        <label className="text-xs">
          <input
            type="checkbox"
            checked={autoHide}
            disabled={busy}
            onChange={(event) => {
              const enabled = event.target.checked;
              void run(async () => {
                await setMessageRequestHistoryPreference(enabled);
              });
            }}
          />{" "}
          Automatically remove declined, withdrawn and expired requests from my
          history
        </label>
      </div>
      <p className="text-xs text-[var(--text-subtle)]">
        History cleanup affects your view only. The other person's history and
        shared records are retained.
      </p>
      {error ? (
        <p role="alert" className="text-sm">
          {error}
        </p>
      ) : null}
      <ul className="space-y-2">
        {requests.map((request) => (
          <li
            key={request.request_id}
            className="rounded border border-[var(--panel-border)] p-2"
            data-testid="message-request-row"
          >
            <p className="text-sm">
              {request.outgoing ? "To" : "From"}{" "}
              {peerPresentationLabel(request.peer)} · {request.state}
            </p>
            <p className="whitespace-pre-wrap break-words text-sm">
              {request.note}
            </p>
            <p className="text-xs">
              Requested {new Date(request.created_at).toLocaleDateString()}
            </p>
            {request.state === "pending" ? (
              request.outgoing ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void changeRequest(request, "withdraw")}
                >
                  Withdraw request
                </button>
              ) : (
                <div className="flex gap-3">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void changeRequest(request, "accept")}
                  >
                    Accept request
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void changeRequest(request, "decline")}
                  >
                    Decline request
                  </button>
                </div>
              )
            ) : (
              <div className="flex gap-3">
                {request.conversation_id ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await onAccepted(request.conversation_id!);
                      })
                    }
                  >
                    Open conversation
                  </button>
                ) : null}
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      await archiveMessageRequest(request.request_id);
                    })
                  }
                >
                  Remove from my history
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {requests.length === 0 ? (
        <p className="text-xs">
          {history ? "No retained request history." : "No pending requests."}
        </p>
      ) : null}
    </section>
  );
}
