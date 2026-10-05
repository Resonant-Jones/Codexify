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
