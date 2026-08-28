#!/usr/bin/env node
import { registerBunOAuthFlows } from "@earendil-works/pi-ai/bun-oauth";
import { APP_NAME } from "../config.js";
process.title = APP_NAME;
process.emitWarning = (() => { });
registerBunOAuthFlows();
import { restoreSandboxEnv } from "./restore-sandbox-env.js";
restoreSandboxEnv();
await import("./register-bedrock.js");
await import("../cli.js");
//# sourceMappingURL=cli.js.map