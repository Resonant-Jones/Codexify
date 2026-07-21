declare namespace chrome {
  namespace runtime {
    interface ExtensionEvent<Listener extends (...args: never[]) => void> {
      addListener(listener: Listener): void
    }

    const onInstalled: ExtensionEvent<() => void>
    const onStartup: ExtensionEvent<() => void>
  }

  namespace sidePanel {
    function setPanelBehavior(behavior: {
      openPanelOnActionClick: boolean
    }): Promise<void>
  }

  namespace storage {
    interface StorageArea {
      get(keys?: string | string[] | Record<string, unknown> | null): Promise<Record<string, unknown>>
      set(items: Record<string, unknown>): Promise<void>
      remove(keys: string | string[]): Promise<void>
      setAccessLevel?(options: {
        accessLevel: "TRUSTED_CONTEXTS" | "TRUSTED_AND_UNTRUSTED_CONTEXTS"
      }): Promise<void>
    }

    const local: StorageArea
  }

  namespace permissions {
    interface Permissions {
      origins?: string[]
      permissions?: string[]
    }

    function request(permissions: Permissions): Promise<boolean>
    function contains(permissions: Permissions): Promise<boolean>
    function remove(permissions: Permissions): Promise<boolean>
  }
}
