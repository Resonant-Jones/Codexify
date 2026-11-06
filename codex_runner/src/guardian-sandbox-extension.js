/**
 * Guardian sandbox extension for Pi.
 *
 * Installs a bash tool whose spawn hook rewrites every command into a call to
 * the local Guardian sandbox proxy. The proxy forwards the command to the
 * Guardian sandbox route, which dispatches it to the configured provider
 * sandbox; the proxy then reproduces the remote stdout/stderr/exit code as
 * its own.
 *
 * The model keeps calling the ordinary `bash` tool, so the tool-call contract
 * is preserved. Only the execution location changes.
 *
 * Extension tools replace built-in tools of the same name in Pi's tool
 * registry, so registering `bash` here is what makes the rewrite effective.
 *
 * A spawn hook can only rewrite a command -- it cannot host execution
 * somewhere else -- so the rewrite targets a local proxy rather than calling
 * the provider directly.
 */

/**
 * Build the inline extension factory that installs the sandboxed bash tool.
 *
 * @param {object} options
 * @param {(cwd: string, opts: object) => object} options.createBashTool
 *        Pi SDK factory for the bash tool.
 * @param {string} options.proxyPath Absolute path to the sandbox proxy.
 * @param {string} options.cwd Session working directory.
 * @returns {(pi: object) => void} An inline Pi extension factory.
 */
export function createGuardianSandboxExtensionFactory({
	createBashTool,
	proxyPath,
	cwd,
}) {
	return function guardianSandboxExtension(pi) {
		const bashTool = createBashTool(cwd, {
			spawnHook: ({ command, cwd: spawnCwd, env }) => ({
				command: proxyPath,
				cwd: spawnCwd,
				env: {
					...env,
					CODEXIFY_SANDBOX_COMMAND: command,
					CODEXIFY_SANDBOX_CWD: spawnCwd,
				},
			}),
		});

		pi.registerTool({
			...bashTool,
			execute: async (id, params, signal, onUpdate, ctx) =>
				bashTool.execute(id, params, signal, onUpdate, ctx),
		});
	};
}

/**
 * Read the sandbox wiring configuration from the environment.
 *
 * Returns `null` when sandbox mode is not requested. When sandbox mode *is*
 * requested but misconfigured, the returned object carries `missing` so the
 * caller can fail closed instead of silently executing locally.
 *
 * @param {NodeJS.ProcessEnv} env
 * @returns {{missing: string[], proxyPath: string, cwd: string} | null}
 */
export function readSandboxExtensionConfig(env = process.env) {
	const enabled = (env.CODEXIFY_PI_SANDBOX_ENABLED || "").trim().toLowerCase();
	if (enabled !== "true" && enabled !== "1" && enabled !== "yes") {
		return null;
	}

	const missing = [
		"CODEXIFY_SANDBOX_API_BASE",
		"CODEXIFY_SANDBOX_API_KEY",
		"CODEXIFY_SANDBOX_WORKSPACE_ARCHIVE",
	].filter((name) => !(env[name] || "").trim());

	return {
		missing,
		proxyPath: (env.CODEXIFY_SANDBOX_PROXY_PATH || "").trim(),
		cwd: (env.CODEXIFY_SANDBOX_CWD || "").trim(),
	};
}

/**
 * Tool names that must not be advertised when a read-only sandbox workspace
 * is in force. `write` and `edit` would otherwise mutate the host filesystem
 * outside the sandbox boundary.
 */
export const SANDBOX_EXCLUDED_TOOL_NAMES = Object.freeze(["write", "edit"]);
