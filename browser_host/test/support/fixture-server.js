"use strict";

const http = require("node:http");

function page(title, body) {
  return `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title></head><body><h1>${title}</h1>${body}</body></html>`;
}

function startFixtureServer({ label = "fixture" } = {}) {
  const requests = [];
  let closed = false;
  const server = http.createServer((request, response) => {
    const url = new URL(request.url, "http://127.0.0.1");
    requests.push({ method: request.method, path: url.pathname, label });
    let status = 200;
    let contentType = "text/html; charset=utf-8";
    let body = page("Primary fixture", '<p id="fixture-text">Synthetic same-origin Browser Host fixture.</p><a id="secondary" href="/secondary">Secondary fixture</a>');
    if (url.pathname === "/secondary") body = page("Secondary fixture", '<p id="secondary-text">Synthetic same-origin secondary fixture.</p><a href="/">Primary fixture</a>');
    if (url.pathname === "/popup") body = page("Popup denial fixture", '<button id="popup" onclick="window.__popupResult = window.open(\'https://example.com/\')">Open popup</button>');
    if (url.pathname === "/download") body = page("Download denial fixture", '<a id="download" download href="/download-file">Download synthetic file</a>');
    if (url.pathname === "/permission") body = page("Permission denial fixture", '<script>navigator.geolocation.getCurrentPosition(() => window.__permissionResult = "granted", (error) => window.__permissionResult = error.code);</script><p>Permission request issued.</p>');
    if (url.pathname === "/external") body = page("External navigation fixture", '<button id="external" onclick="window.location.href = \'https://example.com/\'">External navigation</button>');
    if (url.pathname === "/download-file") { contentType = "text/plain; charset=utf-8"; response.setHeader("Content-Disposition", "attachment; filename=fixture.txt"); body = "synthetic download"; }
    if (url.pathname === "/health") body = JSON.stringify({ status: "ok", service: "fixture" });
    if (!["/", "/secondary", "/popup", "/download", "/permission", "/external", "/download-file", "/health"].includes(url.pathname)) { status = 404; body = "not found"; }
    response.writeHead(status, { "Content-Type": contentType, "Content-Length": Buffer.byteLength(body) });
    response.end(body);
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.removeListener("error", reject);
      const address = server.address();
      resolve(Object.freeze({
        origin: `http://127.0.0.1:${address.port}`,
        requests,
        close: () => {
          if (closed) return Promise.resolve();
          closed = true;
          return new Promise((done) => server.close(() => done()));
        }
      }));
    });
  });
}

module.exports = Object.freeze({ startFixtureServer });
