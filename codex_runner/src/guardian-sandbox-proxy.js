#!/usr/bin/env node
/**
 * Guardian sandbox execution proxy.
 *
 * Pi's bash spawn hook can rewrite a command before it is spawned, but it
 * cannot host execution somewhere else. This proxy is the local end of that
 * rewrite: the spawn hook rewrites `bash <command>` into
 * `guardian-sandbox-proxy`, and this process forwards the command to the
 * Guardian sandbox route and reproduces the remote result as its own
 * stdout/stderr/exit code.
 *
 * The model keeps calling the ordinary `bash` tool, so the tool-call contract
 * is unchanged; only the execution location moves into the provider sandbox.
 *
 * Configuration comes from the environment:
 *   CODEXIFY_SANDBOX_API_BASE       Guardian base URL (required)
 *   CODEXIFY_SANDBOX_API_KEY        operator credential (required)
 *   CODEXIFY_SANDBOX_COMMAND        the original command (set by the hook)
 *   CODEXIFY_SANDBOX_CWD            the original working directory
 *   CODEXIFY_SANDBOX_WORKSPACE_ARCHIVE   prepared workspace archive path
 *   CODEXIFY_SANDBOX_WORKSPACE_IDENTITY  workspace identity label
 *   CODEXIFY_SANDBOX_TIMEOUT_SECONDS      request timeout
 */

import process from "node:process";

function readEnv(name, fallback = "") {
	const value = process.env[name];
	return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function fail(message, code = 2) {
	process.stderr.write(`${message}\n`);
	process.exit(code);
}

async function main() {
	const apiBase = readEnv("CODEXIFY_SANDBOX_API_BASE").replace(/\/+$/, "");
	const apiKey = readEnv("CODEXIFY_SANDBOX_API_KEY");
	const command = readEnv("CODEXIFY_SANDBOX_COMMAND");
	const cwd = readEnv("CODEXIFY_SANDBOX_CWD");
	const archive = readEnv("CODEXIFY_SANDBOX_WORKSPACE_ARCHIVE");
	const identity = readEnv("CODEXIFY_SANDBOX_WORKSPACE_IDENTITY", "guardian-workspace");
	const timeoutSeconds = Number.parseInt(
		readEnv("CODEXIFY_SANDBOX_TIMEOUT_SECONDS", "900"),
		10,
	);

	if (!apiBase) fail("sandbox_proxy_missing_api_base");
	if (!apiKey) fail("sandbox_proxy_missing_api_key");
	if (!command) fail("sandbox_proxy_missing_command");
	if (!archive) fail("sandbox_proxy_missing_workspace_archive");

	const body = {
		command,
		workspace_identity: identity,
		workspace_source: archive,
		principal: "pi-sandbox-proxy",
		timeout_seconds: Number.isFinite(timeoutSeconds) ? timeoutSeconds : 900,
		working_directory: cwd,
	};

	let response;
	try {
		response = await fetch(`${apiBase}/api/sandbox/execute`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-API-Key": apiKey,
			},
			body: JSON.stringify(body),
		});
	} catch (error) {
		fail(`sandbox_proxy_transport_error:${error?.message ?? error}`);
		return;
	}

	const raw = await response.text();
	if (!response.ok) {
		fail(`sandbox_proxy_http_${response.status}:${raw.slice(0, 500)}`, 3);
		return;
	}

	let payload;
	try {
		payload = JSON.parse(raw);
	} catch (error) {
		fail(`sandbox_proxy_invalid_payload:${error?.message ?? error}`, 3);
		return;
	}

	if (payload.stdout) process.stdout.write(payload.stdout);
	if (payload.stderr) process.stderr.write(payload.stderr);

	if (payload.status !== "completed") {
		process.stderr.write(
			`sandbox_status:${payload.status}${payload.reason ? `:${payload.reason}` : ""}\n`,
		);
	}

	const exitCode =
		typeof payload.exit_code === "number" ? payload.exit_code : 1;
	process.exit(exitCode);
}

await main();
