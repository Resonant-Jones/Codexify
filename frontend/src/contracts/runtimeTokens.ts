export const LIVE_EVENT_CONNECTION_STATES = {
  CONNECTING: "connecting",
  CONNECTED: "connected",
  RECONNECTING: "reconnecting",
  DISCONNECTED: "disconnected",
} as const;

export type LiveEventConnectionState =
  (typeof LIVE_EVENT_CONNECTION_STATES)[keyof typeof LIVE_EVENT_CONNECTION_STATES];
