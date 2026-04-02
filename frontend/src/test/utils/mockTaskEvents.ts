export type MockTaskEventHandler = (event: any) => void;

let currentHandler: MockTaskEventHandler | null = null;

export function emitTaskEvent(handler: MockTaskEventHandler, event: any) {
  handler(event);
}

export function setMockTaskEventHandler(handler: MockTaskEventHandler | null) {
  currentHandler = handler;
}

export function emitCurrentTaskEvent(event: any) {
  currentHandler?.(event);
}

export function resetMockTaskEventHandler() {
  currentHandler = null;
}
