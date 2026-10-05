import assert from "node:assert/strict";
import test from "node:test";

import worker from "../src/index.mjs";

async function captureLogs(run) {
  const originalLog = console.log;
  const records = [];
  console.log = (record) => records.push(JSON.parse(record));

  try {
    return { result: await run(), records };
  } finally {
    console.log = originalLog;
  }
}

function guardianHealthResponse(request, payload = {
  service: "guardian",
  capability: "edge.health",
  status: "ok",
}) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "X-Codexify-Edge-Request-ID": request.headers.get(
        "X-Codexify-Edge-Request-ID",
      ),
    },
  });
}

test("GET /healthz identifies the non-authoritative EdgeNode", async () => {
  const { result: response } = await captureLogs(() =>
    worker.fetch(new Request("https://edge.test/healthz")),
  );

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    service: "codexify-edge",
    role: "edge_node",
    status: "ok",
    canonical: false,
  });
});

test("health responses are not cacheable and carry an EdgeNode request ID", async () => {
  const { result: response } = await captureLogs(() =>
    worker.fetch(new Request("https://edge.test/healthz")),
  );

  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.match(response.headers.get("X-Codexify-Edge-Request-ID"), /^[0-9a-f-]{36}$/i);
});

test("separate requests get fresh IDs and ignore caller-provided IDs", async () => {
  const { result: responses } = await captureLogs(async () =>
    Promise.all([
      worker.fetch(
        new Request("https://edge.test/healthz", {
          headers: { "X-Codexify-Edge-Request-ID": "caller-controlled" },
        }),
      ),
      worker.fetch(new Request("https://edge.test/healthz")),
    ]),
  );

  const ids = responses.map((response) =>
    response.headers.get("X-Codexify-Edge-Request-ID"),
  );
  assert.notEqual(ids[0], "caller-controlled");
  assert.notEqual(ids[0], ids[1]);
});

test("unknown routes return a small 404 and do not proxy", async () => {
  const originalFetch = globalThis.fetch;
  let proxyCalled = false;
  globalThis.fetch = async () => {
    proxyCalled = true;
    throw new Error("unexpected proxy request");
  };

  try {
    const { result: response } = await captureLogs(() =>
      worker.fetch(new Request("https://edge.test/does-not-exist")),
    );
    assert.equal(response.status, 404);
    assert.deepEqual(await response.json(), { error: "not_found" });
    assert.equal(proxyCalled, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("unsupported health methods return 405 with the allowed method", async () => {
  const { result: response } = await captureLogs(() =>
    worker.fetch(
      new Request("https://edge.test/healthz", { method: "POST", body: "ignored" }),
    ),
  );

  assert.equal(response.status, 405);
  assert.equal(response.headers.get("Allow"), "GET");
  assert.deepEqual(await response.json(), { error: "method_not_allowed" });
});

test("credentials, query values, and request bodies are neither reflected nor logged", async () => {
  const privateValues = [
    "query-secret-value",
    "bearer-secret-value",
    "cookie-secret-value",
    "private-body-value",
  ];
  const { result: response, records } = await captureLogs(() =>
    worker.fetch(
      new Request("https://edge.test/healthz?token=query-secret-value", {
        method: "POST",
        headers: {
          Authorization: "Bearer bearer-secret-value",
          Cookie: "session=cookie-secret-value",
        },
        body: "private-body-value",
      }),
    ),
  );

  const responseText = await response.text();
  const logText = JSON.stringify(records);
  for (const value of privateValues) {
    assert.equal(responseText.includes(value), false);
    assert.equal(logText.includes(value), false);
  }
  assert.equal(records.length, 1);
  assert.deepEqual(Object.keys(records[0]).sort(), [
    "edge_request_id",
    "event",
    "method",
    "pathname",
    "status",
  ]);
});

test("one structured bounded log record is emitted per handled request", async () => {
  const { result: response, records } = await captureLogs(() =>
    worker.fetch(
      new Request("https://edge.test/healthz", {
        headers: { "cf-ray": "0123456789abcdef-SJC" },
      }),
    ),
  );

  assert.equal(records.length, 1);
  assert.equal(records[0].event, "codexify_edge_request");
  assert.equal(
    records[0].edge_request_id,
    response.headers.get("X-Codexify-Edge-Request-ID"),
  );
  assert.equal(records[0].method, "GET");
  assert.equal(records[0].pathname, "/healthz");
  assert.equal(records[0].status, 200);
  assert.equal(records[0].cf_ray, "0123456789abcdef-SJC");
});

test("Guardian health uses one fixed VPC request and a bounded response", async () => {
  let upstreamRequest;
  let publicFetchCalled = false;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    publicFetchCalled = true;
    throw new Error("public fetch must not be used for the private capability");
  };
  const env = {
    GUARDIAN_EDGE_CAPABILITY_KEY: "edge-capability-test-secret",
    GUARDIAN_CAPABILITY: {
      async fetch(request) {
        upstreamRequest = request;
        return guardianHealthResponse(request);
      },
    },
  };

  let response;
  let records;
  try {
    ({ result: response, records } = await captureLogs(() =>
      worker.fetch(new Request("https://edge.test/capabilities/guardian-health"), env),
    ));
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    service: "codexify-edge",
    capability: "guardian.health",
    status: "ok",
    upstream: "guardian",
  });
  assert.equal(publicFetchCalled, false);
  assert.equal(records.length, 1);
  assert.equal(records[0].upstream_outcome, "ok");
  assert.equal(upstreamRequest.url, "http://guardian-vpc.internal/api/internal/edge/health");
  assert.equal(upstreamRequest.method, "GET");
  assert.deepEqual(Object.fromEntries(upstreamRequest.headers.entries()), {
    "x-api-key": "edge-capability-test-secret",
    "x-codexify-edge-request-id": response.headers.get(
      "X-Codexify-Edge-Request-ID",
    ),
  });
  assert.equal(upstreamRequest.body, null);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
});

test("Guardian health ignores caller credentials and query data", async () => {
  let upstreamRequest;
  const env = {
    GUARDIAN_EDGE_CAPABILITY_KEY: "edge-capability-test-secret",
    GUARDIAN_CAPABILITY: {
      async fetch(request) {
        upstreamRequest = request;
        return guardianHealthResponse(request);
      },
    },
  };

  const { result: response } = await captureLogs(() =>
    worker.fetch(
      new Request("https://edge.test/capabilities/guardian-health?token=query-secret", {
        headers: {
          Authorization: "Bearer caller-bearer",
          Cookie: "gc_session=caller-cookie",
          "X-API-Key": "caller-api-key",
          "X-Codexify-Edge-Request-ID": "caller-request-id",
        },
      }),
      env,
    ),
  );

  assert.equal(response.status, 200);
  assert.equal(upstreamRequest.url, "http://guardian-vpc.internal/api/internal/edge/health");
  assert.equal(upstreamRequest.headers.has("authorization"), false);
  assert.equal(upstreamRequest.headers.has("cookie"), false);
  assert.notEqual(upstreamRequest.headers.get("x-api-key"), "caller-api-key");
  assert.notEqual(
    upstreamRequest.headers.get("X-Codexify-Edge-Request-ID"),
    "caller-request-id",
  );
  assert.equal(upstreamRequest.url.includes("query-secret"), false);
  assert.equal(upstreamRequest.body, null);
});

test("Guardian health fails closed when binding or secret is unavailable", async () => {
  const { result: noBinding } = await captureLogs(() =>
    worker.fetch(
      new Request("https://edge.test/capabilities/guardian-health"),
      { GUARDIAN_EDGE_CAPABILITY_KEY: "edge-secret" },
    ),
  );
  assert.equal(noBinding.status, 503);

  let bindingCalled = false;
  const { result: noSecret } = await captureLogs(() =>
    worker.fetch(
      new Request("https://edge.test/capabilities/guardian-health"),
      {
        GUARDIAN_CAPABILITY: {
          async fetch() {
            bindingCalled = true;
            return new Response(null, { status: 200 });
          },
        },
      },
    ),
  );
  assert.equal(noSecret.status, 503);
  assert.equal(bindingCalled, false);
});

test("Guardian health rejects unsupported methods without calling VPC", async () => {
  let bindingCalled = false;
  const { result: response } = await captureLogs(() =>
    worker.fetch(
      new Request("https://edge.test/capabilities/guardian-health", {
        method: "POST",
        body: "ignored",
      }),
      {
        GUARDIAN_EDGE_CAPABILITY_KEY: "edge-secret",
        GUARDIAN_CAPABILITY: {
          async fetch() {
            bindingCalled = true;
            throw new Error("unexpected VPC request");
          },
        },
      },
    ),
  );

  assert.equal(response.status, 405);
  assert.equal(response.headers.get("Allow"), "GET");
  assert.equal(bindingCalled, false);
});

test("Guardian health rejects uncorrelated or failed Guardian responses", async () => {
  const env = {
    GUARDIAN_EDGE_CAPABILITY_KEY: "edge-secret",
    GUARDIAN_CAPABILITY: {
      async fetch() {
        return new Response("private upstream details", { status: 200 });
      },
    },
  };
  const { result: mismatch } = await captureLogs(() =>
    worker.fetch(new Request("https://edge.test/capabilities/guardian-health"), env),
  );
  assert.equal(mismatch.status, 502);
  assert.deepEqual(await mismatch.json(), {
    error: "guardian_capability_unavailable",
  });

  env.GUARDIAN_CAPABILITY.fetch = async () =>
    new Response("private upstream details", {
      status: 503,
      headers: { "X-Codexify-Edge-Request-ID": "not-the-generated-id" },
    });
  const { result: failed } = await captureLogs(() =>
    worker.fetch(new Request("https://edge.test/capabilities/guardian-health"), env),
  );
  assert.equal(failed.status, 502);
  assert.equal((await failed.text()).includes("private upstream details"), false);
});

test("Guardian health rejects authorization failures and malformed responses", async () => {
  const env = {
    GUARDIAN_EDGE_CAPABILITY_KEY: "edge-secret",
    GUARDIAN_CAPABILITY: {},
  };
  for (const status of [401, 403]) {
    env.GUARDIAN_CAPABILITY.fetch = async (request) =>
      new Response("unauthorized", {
        status,
        headers: {
          "X-Codexify-Edge-Request-ID": request.headers.get(
            "X-Codexify-Edge-Request-ID",
          ),
        },
      });
    const { result: unauthorized, records: unauthorizedLogs } = await captureLogs(
      () => worker.fetch(new Request("https://edge.test/capabilities/guardian-health"), env),
    );
    assert.equal(unauthorized.status, 502);
    assert.deepEqual(await unauthorized.json(), {
      error: "guardian_capability_unavailable",
    });
    assert.equal(unauthorizedLogs[0].upstream_outcome, "guardian_rejected");
  }

  env.GUARDIAN_CAPABILITY.fetch = async (request) =>
    new Response("not-json", {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "X-Codexify-Edge-Request-ID": request.headers.get(
          "X-Codexify-Edge-Request-ID",
        ),
      },
    });
  const { result: malformed } = await captureLogs(() =>
    worker.fetch(new Request("https://edge.test/capabilities/guardian-health"), env),
  );
  assert.equal(malformed.status, 502);
  assert.deepEqual(await malformed.json(), {
    error: "guardian_capability_unavailable",
  });
});

test("Guardian health rejects oversized upstream bodies", async () => {
  const { result: response } = await captureLogs(() =>
    worker.fetch(new Request("https://edge.test/capabilities/guardian-health"), {
      GUARDIAN_EDGE_CAPABILITY_KEY: "edge-secret",
      GUARDIAN_CAPABILITY: {
        async fetch(request) {
          return new Response("x".repeat(2048), {
            status: 200,
            headers: {
              "Content-Type": "application/json",
              "X-Codexify-Edge-Request-ID": request.headers.get(
                "X-Codexify-Edge-Request-ID",
              ),
            },
          });
        },
      },
    }),
  );

  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), {
    error: "guardian_capability_unavailable",
  });
});

test("Guardian health bounds time and converts VPC errors to a small 502", async () => {
  let receivedSignal;
  const { result: response } = await captureLogs(() =>
    worker.fetch(
      new Request("https://edge.test/capabilities/guardian-health"),
      {
        GUARDIAN_EDGE_CAPABILITY_KEY: "edge-secret",
        GUARDIAN_CAPABILITY: {
          async fetch(request) {
            receivedSignal = request.signal;
            return new Promise((resolve, reject) => {
              request.signal.addEventListener(
                "abort",
                () => reject(new Error("private timeout details")),
                { once: true },
              );
            });
          },
        },
      },
    ),
  );

  assert.equal(response.status, 502);
  assert.equal(receivedSignal.aborted, true);
  assert.deepEqual(await response.json(), {
    error: "guardian_capability_unavailable",
  });
});
