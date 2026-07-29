/// <reference path="./chrome.d.ts" />

import {
  createRemoteSessionCredential,
  deserializeConnectionProfile,
  serializeConnectionProfile,
  type ConnectionProfile,
  type RemoteSessionCredential,
} from "./connectionProfile"

export const CONNECTION_PROFILE_STORAGE_KEY = "codexify.connection-profile.v2"
export const LEGACY_CONNECTION_PROFILE_STORAGE_KEY = "codexify.connection-profile.v1"
export const CONNECTION_SESSION_STORAGE_KEY = "codexify.connection-session.v1"

export interface ChromeStorageAreaLike {
  get(keys?: string | string[] | Record<string, unknown> | null): Promise<Record<string, unknown>>
  set(items: Record<string, unknown>): Promise<void>
  remove(keys: string | string[]): Promise<void>
  setAccessLevel?(options: { accessLevel: "TRUSTED_CONTEXTS" }): Promise<void>
}

export interface ConnectionStorage {
  load(): Promise<ConnectionProfile | null>
  save(profile: ConnectionProfile): Promise<void>
  loadRemoteSession(): Promise<RemoteSessionCredential | null>
  saveRemoteSession(credential: RemoteSessionCredential): Promise<void>
  clearRemoteSession(): Promise<void>
  updateSelectedThreadId(selectedThreadId: number | null): Promise<void>
  clear(): Promise<void>
}

function deserializeRemoteSession(value: unknown): RemoteSessionCredential | null {
  if (!value || typeof value !== "object") return null
  const record = value as Record<string, unknown>
  if (
    typeof record.token !== "string" ||
    typeof record.userId !== "string" ||
    typeof record.expiresAt !== "number"
  ) {
    return null
  }
  try {
    return createRemoteSessionCredential({
      token: record.token,
      userId: record.userId,
      expiresAt: record.expiresAt,
    })
  } catch {
    return null
  }
}

export function createChromeConnectionStorage(
  suppliedLocalArea?: ChromeStorageAreaLike,
  suppliedSessionArea?: ChromeStorageAreaLike,
): ConnectionStorage {
  const getLocalArea = (): ChromeStorageAreaLike => suppliedLocalArea ?? chrome.storage.local
  const getSessionArea = (): ChromeStorageAreaLike => suppliedSessionArea ?? chrome.storage.session

  return {
    async load() {
      const area = getLocalArea()
      const result = await area.get([
        CONNECTION_PROFILE_STORAGE_KEY,
        LEGACY_CONNECTION_PROFILE_STORAGE_KEY,
      ])
      const currentRaw = result[CONNECTION_PROFILE_STORAGE_KEY]
      const legacyRaw = result[LEGACY_CONNECTION_PROFILE_STORAGE_KEY]
      const rawProfile = currentRaw ?? legacyRaw
      const profile = deserializeConnectionProfile(rawProfile)
      if (rawProfile !== undefined && profile === null) {
        await area.remove([
          CONNECTION_PROFILE_STORAGE_KEY,
          LEGACY_CONNECTION_PROFILE_STORAGE_KEY,
        ])
        return null
      }
      if (profile && legacyRaw !== undefined && currentRaw === undefined) {
        await this.save(profile)
      }
      return profile
    },

    async save(profile) {
      const area = getLocalArea()
      await area.setAccessLevel?.({ accessLevel: "TRUSTED_CONTEXTS" })
      await area.set({
        [CONNECTION_PROFILE_STORAGE_KEY]: serializeConnectionProfile(profile),
      })
      await area.remove(LEGACY_CONNECTION_PROFILE_STORAGE_KEY)
    },

    async loadRemoteSession() {
      const area = getSessionArea()
      const result = await area.get(CONNECTION_SESSION_STORAGE_KEY)
      const rawCredential = result[CONNECTION_SESSION_STORAGE_KEY]
      const credential = deserializeRemoteSession(rawCredential)
      if (rawCredential !== undefined && credential === null) {
        await area.remove(CONNECTION_SESSION_STORAGE_KEY)
      }
      return credential
    },

    async saveRemoteSession(credential) {
      const area = getSessionArea()
      await area.setAccessLevel?.({ accessLevel: "TRUSTED_CONTEXTS" })
      await area.set({
        [CONNECTION_SESSION_STORAGE_KEY]: createRemoteSessionCredential(credential),
      })
    },

    async clearRemoteSession() {
      await getSessionArea().remove(CONNECTION_SESSION_STORAGE_KEY)
    },

    async updateSelectedThreadId(selectedThreadId) {
      const current = await this.load()
      if (!current) return
      await this.save({ ...current, selectedThreadId })
    },

    async clear() {
      await Promise.all([
        getLocalArea().remove([
          CONNECTION_PROFILE_STORAGE_KEY,
          LEGACY_CONNECTION_PROFILE_STORAGE_KEY,
        ]),
        getSessionArea().remove(CONNECTION_SESSION_STORAGE_KEY),
      ])
    },
  }
}

export const chromeConnectionStorage = createChromeConnectionStorage()
