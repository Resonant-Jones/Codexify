declare namespace chrome {
  namespace runtime {
    interface ExtensionEvent<Listener extends (...args: never[]) => void> {
      addListener(listener: Listener): void
    }

    interface MessageSender {
      tab?: tabs.Tab
    }

    type RuntimeMessageListener = (
      message: unknown,
      sender: MessageSender,
      sendResponse: (response?: unknown) => void,
    ) => boolean | void

    function sendMessage<TResponse>(message: unknown): Promise<TResponse>

    const onInstalled: ExtensionEvent<() => void>
    const onStartup: ExtensionEvent<() => void>
    const onMessage: ExtensionEvent<RuntimeMessageListener>
  }

  namespace tabs {
    interface Tab {
      id?: number
      index?: number
      windowId?: number
      active?: boolean
      url?: string
      title?: string
    }

    function query(queryInfo: {
      active?: boolean
      currentWindow?: boolean
      lastFocusedWindow?: boolean
    }): Promise<Tab[]>
  }

  namespace scripting {
    interface InjectionResult<T = unknown> {
      frameId?: number
      documentId?: string
      result?: T
    }

    function executeScript<TArgs extends unknown[], TResult>(injection: {
      target: { tabId: number; allFrames?: boolean }
      func: (...args: TArgs) => TResult
      args?: TArgs
    }): Promise<Array<InjectionResult<TResult>>>
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
    const session: StorageArea
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
