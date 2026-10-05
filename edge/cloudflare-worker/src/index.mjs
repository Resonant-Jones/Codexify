const REQUEST_ID_HEADER = "X-Codexify-Edge-Request-ID";
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

export default {
  async fetch(request) {
    const requestId = crypto.randomUUID();
    const url = new URL(request.url);
    const method = request.method.toUpperCase();
    const pathname = url.pathname;

    let status;
    let payload;
    let allow;

    if (pathname !== "/healthz") {
      status = 404;
      payload = { error: "not_found" };
    } else if (method !== "GET") {
      status = 405;
      payload = { error: "method_not_allowed" };
      allow = "GET";
    } else {
      status = 200;
      payload = {
        service: "codexify-edge",
        role: "edge_node",
        status: "ok",
        canonical: false,
      };
    }

    const response = jsonResponse(status, payload, requestId, allow);
    const logRecord = {
      event: "codexify_edge_request",
      edge_request_id: requestId,
      method,
      pathname,
      status,
    };
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
