const REQUEST_ID_HEADER = "X-Codexify-Edge-Request-ID";
const GUARDIAN_CAPABILITY_PATH = "/capabilities/guardian-health";
const GUARDIAN_CAPABILITY_URL =
  "http://guardian-vpc.internal/api/internal/edge/health";
const GUARDIAN_CAPABILITY_TIMEOUT_MS = 4000;
const GUARDIAN_RESPONSE_MAX_BYTES = 1024;
const RAY_ID_PATTERN = /^[0-9a-f]{16,32}(?:-[a-z]{3})?$/i;
const COLO_PATTERN = /^[a-z]{3}$/i;

function jsonResponse(status, payload, requestId, allow) {
  const headers = new Headers({
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
    [REQUEST_ID_HEADER]: requestId,
  });

  if (allow) {
    headers.set("Allow", allow);
  }

  return new Response(JSON.stringify(payload), { status, headers });
}

async function discardResponseBody(response) {
  try {
    await response.body?.cancel();
  } catch {
    // The upstream body is never forwarded or logged.
  }
}

async function readBoundedGuardianPayload(response) {
  const contentType = response.headers.get("Content-Type") || "";
  if (!/^application\/json(?:\s*;|$)/i.test(contentType)) {
    await discardResponseBody(response);
    return null;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    return null;
  }

  const chunks = [];
  let byteLength = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      byteLength += value.byteLength;
      if (byteLength > GUARDIAN_RESPONSE_MAX_BYTES) {
        await reader.cancel();
        return null;
      }
      chunks.push(value);
    }

    const bytes = new Uint8Array(byteLength);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return null;
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // The stream may already have been cancelled.
    }
  }
}

function isGuardianHealthPayload(payload) {
  return (
    payload !== null &&
    typeof payload === "object" &&
    !Array.isArray(payload) &&
    Object.keys(payload).length === 3 &&
    payload.service === "guardian" &&
    payload.capability === "edge.health" &&
    payload.status === "ok"
  );
}

async function callGuardianHealth(env, requestId) {
  const binding = env?.GUARDIAN_CAPABILITY;
  const capabilityKey = env?.GUARDIAN_EDGE_CAPABILITY_KEY;
  if (
    !binding ||
    typeof binding.fetch !== "function" ||
    typeof capabilityKey !== "string" ||
    capabilityKey.length === 0
  ) {
    return {
      status: 503,
      payload: { error: "guardian_capability_unavailable" },
      upstreamOutcome: "unconfigured",
    };
  }

  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    GUARDIAN_CAPABILITY_TIMEOUT_MS,
  );

  try {
    const upstreamRequest = new Request(GUARDIAN_CAPABILITY_URL, {
      method: "GET",
      headers: {
        "X-API-Key": capabilityKey,
        [REQUEST_ID_HEADER]: requestId,
      },
      redirect: "manual",
      signal: controller.signal,
    });
    const upstreamResponse = await binding.fetch(upstreamRequest);
    if (upstreamResponse.status !== 200) {
      await discardResponseBody(upstreamResponse);
      return {
        status: 502,
        payload: { error: "guardian_capability_unavailable" },
        upstreamOutcome:
          upstreamResponse.status === 401 || upstreamResponse.status === 403
            ? "guardian_rejected"
            : "guardian_status",
      };
    }

    if (upstreamResponse.headers.get(REQUEST_ID_HEADER) !== requestId) {
      await discardResponseBody(upstreamResponse);
      return {
        status: 502,
        payload: { error: "guardian_capability_unavailable" },
        upstreamOutcome: "correlation_mismatch",
      };
    }

    const guardianPayload = await readBoundedGuardianPayload(upstreamResponse);
    if (!isGuardianHealthPayload(guardianPayload)) {
      return {
        status: 502,
        payload: { error: "guardian_capability_unavailable" },
        upstreamOutcome: "invalid_response",
      };
    }

    return {
      status: 200,
      payload: {
        service: "codexify-edge",
        capability: "guardian.health",
        status: "ok",
        upstream: "guardian",
      },
      upstreamOutcome: "ok",
    };
  } catch {
    return {
      status: 502,
      payload: { error: "guardian_capability_unavailable" },
      upstreamOutcome: controller.signal.aborted ? "timeout" : "transport_error",
    };
  } finally {
    clearTimeout(timeout);
  }
}

export default {
  async fetch(request, env) {
    const requestId = crypto.randomUUID();
    const url = new URL(request.url);
    const method = request.method.toUpperCase();
    const pathname = url.pathname;

    let status;
    let payload;
    let allow;
    let upstreamOutcome;

    if (pathname === "/healthz" && method !== "GET") {
      status = 405;
      payload = { error: "method_not_allowed" };
      allow = "GET";
    } else if (pathname === "/healthz") {
      status = 200;
      payload = {
        service: "codexify-edge",
        role: "edge_node",
        status: "ok",
        canonical: false,
      };
    } else if (
      pathname === GUARDIAN_CAPABILITY_PATH &&
      method !== "GET"
    ) {
      status = 405;
      payload = { error: "method_not_allowed" };
      allow = "GET";
    } else if (pathname === GUARDIAN_CAPABILITY_PATH) {
      const result = await callGuardianHealth(env, requestId);
      status = result.status;
      payload = result.payload;
      upstreamOutcome = result.upstreamOutcome;
    } else {
      status = 404;
      payload = { error: "not_found" };
    }

    const response = jsonResponse(status, payload, requestId, allow);
    const logRecord = {
      event: "codexify_edge_request",
      edge_request_id: requestId,
      method,
      pathname,
      status,
    };
    if (pathname === GUARDIAN_CAPABILITY_PATH) {
      logRecord.upstream_outcome = upstreamOutcome || "not_attempted";
    }
    const rayId = request.headers.get("cf-ray");
    if (rayId && RAY_ID_PATTERN.test(rayId)) {
      logRecord.cf_ray = rayId;
    }
    const colo = request.cf?.colo;
    if (typeof colo === "string" && COLO_PATTERN.test(colo)) {
      logRecord.colo = colo.toUpperCase();
    }

    console.log(JSON.stringify(logRecord));
    return response;
  },
};
