/// <reference path="./chrome.d.ts" />

export const CONNECTION_PROFILE_VERSION = 1 as const

export interface ConnectionProfile {
  version: typeof CONNECTION_PROFILE_VERSION
  backendBaseUrl: string
  apiKey: string
  selectedThreadId: number | null
  connectedAt: string
  lastVerifiedAt: string
}

export interface ConnectionProfileInput {
  backendBaseUrl: string
  apiKey: string
  selectedThreadId?: number | null
  connectedAt?: string
  lastVerifiedAt?: string
}

export interface ConnectionProfileSummary {
  backendBaseUrl: string
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
  input: ConnectionProfileInput,
  now = new Date().toISOString(),
): ConnectionProfile {
  const apiKey = input.apiKey.trim()
  if (!apiKey) {
    throw new ConnectionProfileError("Enter the authentication API key.")
  }

  const connectedAt = input.connectedAt ?? now
  return {
    version: CONNECTION_PROFILE_VERSION,
    backendBaseUrl: normalizeBackendBaseUrl(input.backendBaseUrl),
    apiKey,
    selectedThreadId: input.selectedThreadId ?? null,
    connectedAt,
    lastVerifiedAt: input.lastVerifiedAt ?? now,
  }
}

export function serializeConnectionProfile(
  profile: ConnectionProfile,
): ConnectionProfile {
  return {
    version: CONNECTION_PROFILE_VERSION,
    backendBaseUrl: normalizeBackendBaseUrl(profile.backendBaseUrl),
    apiKey: profile.apiKey,
    selectedThreadId: profile.selectedThreadId,
    connectedAt: profile.connectedAt,
    lastVerifiedAt: profile.lastVerifiedAt,
  }
}

export function deserializeConnectionProfile(value: unknown): ConnectionProfile | null {
  if (!value || typeof value !== "object") return null

  const record = value as Record<string, unknown>
  if (record.version !== CONNECTION_PROFILE_VERSION) return null
  if (typeof record.backendBaseUrl !== "string") return null
  if (typeof record.apiKey !== "string" || !record.apiKey.trim()) return null
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

  try {
    return createConnectionProfile({
      backendBaseUrl: record.backendBaseUrl,
      apiKey: record.apiKey,
      selectedThreadId,
      connectedAt: record.connectedAt,
      lastVerifiedAt: record.lastVerifiedAt,
    })
  } catch {
    return null
  }
}

export function summarizeConnectionProfile(
  profile: ConnectionProfile,
): ConnectionProfileSummary {
  return {
    backendBaseUrl: profile.backendBaseUrl,
    selectedThreadId: profile.selectedThreadId,
    connectedAt: profile.connectedAt,
    lastVerifiedAt: profile.lastVerifiedAt,
    hasStoredCredential: Boolean(profile.apiKey),
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
