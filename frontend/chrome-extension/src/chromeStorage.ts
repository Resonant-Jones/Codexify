/// <reference path="./chrome.d.ts" />

import {
  deserializeConnectionProfile,
  serializeConnectionProfile,
  type ConnectionProfile,
} from "./connectionProfile"

export const CONNECTION_PROFILE_STORAGE_KEY = "codexify.connection-profile.v1"

export interface ChromeStorageAreaLike {
  get(keys?: string | string[] | Record<string, unknown> | null): Promise<Record<string, unknown>>
  set(items: Record<string, unknown>): Promise<void>
  remove(keys: string | string[]): Promise<void>
  setAccessLevel?(options: { accessLevel: "TRUSTED_CONTEXTS" }): Promise<void>
}

export interface ConnectionStorage {
  load(): Promise<ConnectionProfile | null>
  save(profile: ConnectionProfile): Promise<void>
  updateSelectedThreadId(selectedThreadId: number | null): Promise<void>
  clear(): Promise<void>
}

export function createChromeConnectionStorage(
  suppliedArea?: ChromeStorageAreaLike,
): ConnectionStorage {
  const getArea = (): ChromeStorageAreaLike => suppliedArea ?? chrome.storage.local

  return {
    async load() {
      const area = getArea()
      const result = await area.get(CONNECTION_PROFILE_STORAGE_KEY)
      const rawProfile = result[CONNECTION_PROFILE_STORAGE_KEY]
      const profile = deserializeConnectionProfile(rawProfile)
      if (rawProfile !== undefined && profile === null) {
        await area.remove(CONNECTION_PROFILE_STORAGE_KEY)
      }
      return profile
    },

    async save(profile) {
      const area = getArea()
      await area.setAccessLevel?.({ accessLevel: "TRUSTED_CONTEXTS" })
      await area.set({
        [CONNECTION_PROFILE_STORAGE_KEY]: serializeConnectionProfile(profile),
      })
    },

    async updateSelectedThreadId(selectedThreadId) {
      const current = await this.load()
      if (!current) return
      await this.save({ ...current, selectedThreadId })
    },

    async clear() {
      await getArea().remove(CONNECTION_PROFILE_STORAGE_KEY)
    },
  }
}

export const chromeConnectionStorage = createChromeConnectionStorage()
