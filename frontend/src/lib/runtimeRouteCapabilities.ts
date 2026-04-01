import { useEffect, useSyncExternalStore } from "react";

import { buildAuthenticatedFetchInit } from "@/lib/api";
import { resolveBackendUrl } from "@/lib/runtimeConfig";
import {
  ALL_SUPPORTED_PROFILE_ROUTE_LABELS,
  isSupportedProfileRouteLabel,
  type RuntimeRouteCapabilityState,
  type SupportedProfileRouteLabel,
} from "@/contracts/supportedProfileRoutes";

type SupportedProfileHealthPayload = {
  supported_profile?: {
    routes?: {
      mounted?: unknown;
      declared?: unknown;
    } | null;
  } | null;
};

type CapabilityStateMap = Record<
  SupportedProfileRouteLabel,
  RuntimeRouteCapabilityState
>;

type RuntimeRouteCapabilitySnapshot = {
  declared: Readonly<Record<string, string>>;
  mounted: readonly SupportedProfileRouteLabel[];
  ready: boolean;
  states: Readonly<CapabilityStateMap>;
};

const listeners = new Set<() => void>();
const forcedUnavailable = new Set<SupportedProfileRouteLabel>();

let loadPromise: Promise<void> | null = null;
let mountedLabels: SupportedProfileRouteLabel[] = [];
let declaredRoutes: Record<string, string> = {};
let routeAvailabilityKnown = false;
let ready = false;
let snapshotRevision = 0;
let cachedSnapshotRevision = -1;
let cachedSnapshot: RuntimeRouteCapabilitySnapshot | null = null;

function createUnknownStateMap(): CapabilityStateMap {
  return ALL_SUPPORTED_PROFILE_ROUTE_LABELS.reduce(
    (accumulator, label) => {
      accumulator[label] = "unknown";
      return accumulator;
    },
    {} as CapabilityStateMap
  );
}

function computeStates(): CapabilityStateMap {
  const next = createUnknownStateMap();
  const mounted = new Set(mountedLabels);

  if (routeAvailabilityKnown) {
    for (const label of ALL_SUPPORTED_PROFILE_ROUTE_LABELS) {
      next[label] = mounted.has(label) ? "available" : "unavailable";
    }
  }

  for (const label of forcedUnavailable) {
    next[label] = "unavailable";
  }

  return next;
}

function getSnapshot(): RuntimeRouteCapabilitySnapshot {
  if (
    cachedSnapshot &&
    cachedSnapshotRevision === snapshotRevision
  ) {
    return cachedSnapshot;
  }

  cachedSnapshot = {
    declared: declaredRoutes,
    mounted: mountedLabels,
    ready,
    states: computeStates(),
  };
  cachedSnapshotRevision = snapshotRevision;
  return cachedSnapshot;
}

function invalidateSnapshot(): void {
  snapshotRevision += 1;
  cachedSnapshot = null;
}

function emitChange(): void {
  for (const listener of listeners) {
    listener();
  }
}

function normalizeDeclaredRoutes(
  value: unknown
): Record<string, string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }

  const next: Record<string, string> = {};
  for (const [key, rawStatus] of Object.entries(value)) {
    if (typeof key !== "string" || !key.trim()) continue;
    if (typeof rawStatus !== "string" || !rawStatus.trim()) continue;
    next[key] = rawStatus;
  }
  return next;
}

function normalizeMountedRoutes(
  value: unknown
): SupportedProfileRouteLabel[] | null {
  if (!Array.isArray(value)) {
    return null;
  }

  const mounted = new Set<SupportedProfileRouteLabel>();
  for (const entry of value) {
    if (isSupportedProfileRouteLabel(entry)) {
      mounted.add(entry);
    }
  }

  return Array.from(mounted);
}

async function loadCapabilities(): Promise<void> {
  try {
    const response = await fetch(
      resolveBackendUrl("/health"),
      buildAuthenticatedFetchInit({
        headers: {
          Accept: "application/json",
        },
      })
    );

    if (!response.ok) {
      throw new Error(`health failed: ${response.status}`);
    }

    const payload = (await response.json()) as SupportedProfileHealthPayload;
    const routes = payload?.supported_profile?.routes;
    const normalizedMounted = normalizeMountedRoutes(routes?.mounted);

    mountedLabels = normalizedMounted ?? [];
    declaredRoutes = normalizeDeclaredRoutes(routes?.declared);
    routeAvailabilityKnown = normalizedMounted !== null;
  } catch {
    mountedLabels = [];
    declaredRoutes = {};
    routeAvailabilityKnown = false;
  } finally {
    ready = true;
    loadPromise = null;
    invalidateSnapshot();
    emitChange();
  }
}

export function ensureRuntimeRouteCapabilitiesLoaded(): Promise<void> {
  if (ready) {
    return Promise.resolve();
  }

  if (!loadPromise) {
    loadPromise = loadCapabilities();
  }

  return loadPromise;
}

export function getRuntimeRouteCapabilityState(
  label: SupportedProfileRouteLabel
): RuntimeRouteCapabilityState {
  return getSnapshot().states[label];
}

export function markRuntimeRouteUnavailable(
  label: SupportedProfileRouteLabel
): void {
  if (forcedUnavailable.has(label)) {
    return;
  }

  forcedUnavailable.add(label);
  invalidateSnapshot();
  emitChange();
}

export function markRuntimeRouteUnavailableIfNotFound(
  label: SupportedProfileRouteLabel,
  error: unknown
): boolean {
  const status = (error as { response?: { status?: unknown } } | null)?.response
    ?.status;
  if (status !== 404) {
    return false;
  }

  markRuntimeRouteUnavailable(label);
  return true;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useRuntimeRouteCapability(label: SupportedProfileRouteLabel): {
  mounted: readonly SupportedProfileRouteLabel[];
  declared: Readonly<Record<string, string>>;
  ready: boolean;
  state: RuntimeRouteCapabilityState;
} {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  useEffect(() => {
    void ensureRuntimeRouteCapabilitiesLoaded();
  }, []);

  return {
    mounted: snapshot.mounted,
    declared: snapshot.declared,
    ready: snapshot.ready,
    state: snapshot.states[label],
  };
}

export function useRuntimeRouteCapabilities(
  labels: readonly SupportedProfileRouteLabel[]
): {
  mounted: readonly SupportedProfileRouteLabel[];
  declared: Readonly<Record<string, string>>;
  ready: boolean;
  states: Partial<CapabilityStateMap>;
} {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  useEffect(() => {
    void ensureRuntimeRouteCapabilitiesLoaded();
  }, []);

  const states: Partial<CapabilityStateMap> = {};
  for (const label of labels) {
    states[label] = snapshot.states[label];
  }

  return {
    mounted: snapshot.mounted,
    declared: snapshot.declared,
    ready: snapshot.ready,
    states,
  };
}

export function __resetRuntimeRouteCapabilitiesForTests(): void {
  loadPromise = null;
  mountedLabels = [];
  declaredRoutes = {};
  routeAvailabilityKnown = false;
  ready = false;
  forcedUnavailable.clear();
  invalidateSnapshot();
  emitChange();
}
