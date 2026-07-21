/// <reference path="./chrome.d.ts" />

export const CONNECTION_PROFILE_VERSION = 2 as const
export const LEGACY_CONNECTION_PROFILE_VERSION = 1 as const

export type ConnectionAuthMode = "local" | "remote"

interface ConnectionProfileBase {
  version: typeof CONNECTION_PROFILE_VERSION
  backendBaseUrl: string
  selectedThreadId: number | null
  connectedAt: string
  lastVerifiedAt: string
}

export interface LocalConnectionProfile extends ConnectionProfileBase {
  authMode: "local"
  apiKey: string
  sessionUserId: null
  sessionExpiresAt: null
}

export interface RemoteConnectionProfile extends ConnectionProfileBase {
  authMode: "remote"
  apiKey: null
  sessionUserId: string
  sessionExpiresAt: number
}

export type ConnectionProfile = LocalConnectionProfile | RemoteConnectionProfile

interface ConnectionProfileInputBase {
  backendBaseUrl: string
  selectedThreadId?: number | null
  connectedAt?: string
  lastVerifiedAt?: string
}

export interface LocalConnectionProfileInput extends ConnectionProfileInputBase {
  apiKey: string
}

export interface RemoteConnectionProfileInput extends ConnectionProfileInputBase {
  sessionUserId: string
  sessionExpiresAt: number
}

export interface RemoteSessionCredential {
  token: string
  userId: string
  expiresAt: number
}

export interface ConnectionProfileSummary {
  backendBaseUrl: string
  authMode: ConnectionAuthMode
  selectedThreadId: number | null
  connectedAt: string
  lastVerifiedAt: string
  hasStoredCredential: boolean
}

export interface OriginPermissionClient {
  request(originPattern: string): Promise<boolean>
  contains(originPattern: string): Promise<boolean>
  remove(originPattern: string): Promise<boolean>
}

export class ConnectionProfileError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "ConnectionProfileError"
  }
}

function parseSupportedBackendUrl(rawValue: string): URL {
  const value = rawValue.trim()
  if (!value) {
    throw new ConnectionProfileError("Enter a Codexify backend URL.")
  }

  let url: URL
  try {
    url = new URL(value)
  } catch {
    throw new ConnectionProfileError("Enter a valid absolute backend URL.")
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new ConnectionProfileError("Only HTTP and HTTPS backend URLs are supported.")
  }
  if (url.username || url.password) {
    throw new ConnectionProfileError("Backend URLs must not contain credentials.")
  }
  if (url.search || url.hash) {
    throw new ConnectionProfileError("Backend URLs must not contain a query or fragment.")
  }

  return url
}

function normalizeSessionUserId(value: string): string {
  const normalized = value.trim()
  if (!normalized) {
    throw new ConnectionProfileError("The remote login did not return a user identity.")
  }
  return normalized
}

function normalizeSessionExpiry(value: number): number {
  if (!Number.isInteger(value) || value <= 0) {
    throw new ConnectionProfileError("The remote login returned an invalid session expiry.")
  }
  return value
}

function connectionProfileBase(
  input: ConnectionProfileInputBase,
  now: string,
): ConnectionProfileBase {
  return {
    version: CONNECTION_PROFILE_VERSION,
    backendBaseUrl: normalizeBackendBaseUrl(input.backendBaseUrl),
    selectedThreadId: input.selectedThreadId ?? null,
    connectedAt: input.connectedAt ?? now,
    lastVerifiedAt: input.lastVerifiedAt ?? now,
  }
}

export function normalizeBackendBaseUrl(rawValue: string): string {
  const url = parseSupportedBackendUrl(rawValue)
  const normalizedPath = url.pathname.replace(/\/+$/u, "")
  return `${url.origin}${normalizedPath && normalizedPath !== "/" ? normalizedPath : ""}`
}

export function getBackendOrigin(rawValue: string): string {
  return new URL(normalizeBackendBaseUrl(rawValue)).origin
}

export function buildOriginPermissionPattern(rawValue: string): string {
  return `${getBackendOrigin(rawValue)}/*`
}

export function createConnectionProfile(
  input: LocalConnectionProfileInput,
  now = new Date().toISOString(),
): LocalConnectionProfile {
  const apiKey = input.apiKey.trim()
  if (!apiKey) {
    throw new ConnectionProfileError("Enter the authentication API key.")
  }

  return {
    ...connectionProfileBase(input, now),
    authMode: "local",
    apiKey,
    sessionUserId: null,
    sessionExpiresAt: null,
  }
}

export function createRemoteConnectionProfile(
  input: RemoteConnectionProfileInput,
  now = new Date().toISOString(),
): RemoteConnectionProfile {
  return {
    ...connectionProfileBase(input, now),
    authMode: "remote",
    apiKey: null,
    sessionUserId: normalizeSessionUserId(input.sessionUserId),
    sessionExpiresAt: normalizeSessionExpiry(input.sessionExpiresAt),
  }
}

export function createRemoteSessionCredential(
  value: RemoteSessionCredential,
): RemoteSessionCredential {
  const token = value.token.trim()
  if (!token) {
    throw new ConnectionProfileError("The remote login did not return a session token.")
  }
  return {
    token,
    userId: normalizeSessionUserId(value.userId),
    expiresAt: normalizeSessionExpiry(value.expiresAt),
  }
}

export function isRemoteSessionUsable(
  credential: RemoteSessionCredential | null,
  profile: RemoteConnectionProfile,
  nowEpochSeconds = Math.floor(Date.now() / 1000),
): credential is RemoteSessionCredential {
  return Boolean(
    credential &&
    credential.userId === profile.sessionUserId &&
    credential.expiresAt === profile.sessionExpiresAt &&
    credential.expiresAt > nowEpochSeconds &&
    credential.token.trim(),
  )
}

export function serializeConnectionProfile(
  profile: ConnectionProfile,
): ConnectionProfile {
  if (profile.authMode === "local") {
    return createConnectionProfile({
      backendBaseUrl: profile.backendBaseUrl,
      apiKey: profile.apiKey,
      selectedThreadId: profile.selectedThreadId,
      connectedAt: profile.connectedAt,
      lastVerifiedAt: profile.lastVerifiedAt,
    })
  }
  return createRemoteConnectionProfile({
    backendBaseUrl: profile.backendBaseUrl,
    sessionUserId: profile.sessionUserId,
    sessionExpiresAt: profile.sessionExpiresAt,
    selectedThreadId: profile.selectedThreadId,
    connectedAt: profile.connectedAt,
    lastVerifiedAt: profile.lastVerifiedAt,
  })
}

function readProfileBase(record: Record<string, unknown>): ConnectionProfileInputBase | null {
  if (typeof record.backendBaseUrl !== "string") return null
  if (typeof record.connectedAt !== "string" || typeof record.lastVerifiedAt !== "string") {
    return null
  }

  const selectedThreadId = record.selectedThreadId
  if (
    selectedThreadId !== null &&
    (typeof selectedThreadId !== "number" || !Number.isInteger(selectedThreadId))
  ) {
    return null
  }

  return {
    backendBaseUrl: record.backendBaseUrl,
    selectedThreadId,
    connectedAt: record.connectedAt,
    lastVerifiedAt: record.lastVerifiedAt,
  }
}

export function deserializeConnectionProfile(value: unknown): ConnectionProfile | null {
  if (!value || typeof value !== "object") return null

  const record = value as Record<string, unknown>
  const base = readProfileBase(record)
  if (!base) return null

  try {
    if (record.version === LEGACY_CONNECTION_PROFILE_VERSION) {
      if (typeof record.apiKey !== "string") return null
      return createConnectionProfile({ ...base, apiKey: record.apiKey })
    }
    if (record.version !== CONNECTION_PROFILE_VERSION) return null

    if (record.authMode === "local") {
      if (typeof record.apiKey !== "string") return null
      return createConnectionProfile({ ...base, apiKey: record.apiKey })
    }
    if (record.authMode === "remote") {
      if (typeof record.sessionUserId !== "string") return null
      if (typeof record.sessionExpiresAt !== "number") return null
      return createRemoteConnectionProfile({
        ...base,
        sessionUserId: record.sessionUserId,
        sessionExpiresAt: record.sessionExpiresAt,
      })
    }
  } catch {
    return null
  }
  return null
}

export function summarizeConnectionProfile(
  profile: ConnectionProfile,
): ConnectionProfileSummary {
  return {
    backendBaseUrl: profile.backendBaseUrl,
    authMode: profile.authMode,
    selectedThreadId: profile.selectedThreadId,
    connectedAt: profile.connectedAt,
    lastVerifiedAt: profile.lastVerifiedAt,
    hasStoredCredential: profile.authMode === "local" ? Boolean(profile.apiKey) : false,
  }
}

export const chromeOriginPermissionClient: OriginPermissionClient = {
  request(originPattern) {
    return chrome.permissions.request({ origins: [originPattern] })
  },
  contains(originPattern) {
    return chrome.permissions.contains({ origins: [originPattern] })
  },
  remove(originPattern) {
    return chrome.permissions.remove({ origins: [originPattern] })
  },
}
