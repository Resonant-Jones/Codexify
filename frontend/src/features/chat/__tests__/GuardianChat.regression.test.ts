/**
 * Regression proof: CANONICAL_SINGLE_USER_ID no longer causes a runtime crash
 * in the Guardian Composer thread-creation path.
 *
 * This test verifies at the source level that:
 * 1. The orphaned CANONICAL_SINGLE_USER_ID reference is gone.
 * 2. The canonical COMMAND_BUS_ACTOR_ID constant is defined and used.
 * 3. Remote-auth mode still omits user_id (the ternary is unchanged).
 *
 * It does not mount the full GuardianChat component, so it avoids the vitest
 * worker-pool instability documented in the task closeout.
 */

import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const SOURCE = path.resolve(
  import.meta.dirname,
  "../GuardianChat.tsx"
);

const sourceText = fs.readFileSync(SOURCE, "utf-8");

describe("Guardian Composer thread-creation identity constant", () => {
  it("has no remaining CANONICAL_SINGLE_USER_ID reference", () => {
    // The primary regression: the orphaned constant would throw
    // ReferenceError at runtime when the composer creates a thread
    // in local-auth mode.
    expect(sourceText).not.toMatch(/CANONICAL_SINGLE_USER_ID/);
  });

  it("defines the canonical COMMAND_BUS_ACTOR_ID with the expected local value", () => {
    // The pre-regression definition was:
    //   const CANONICAL_SINGLE_USER_ID = "local";
    // COMMAND_BUS_ACTOR_ID carries the same value and is used consistently
    // throughout GuardianChat for user_id.
    expect(sourceText).toMatch(/const COMMAND_BUS_ACTOR_ID\s*=\s*"local"/);
  });

  it("uses COMMAND_BUS_ACTOR_ID for the local-auth thread-creation user_id", () => {
    // The fixed line 3163 payload spread must reference the defined constant.
    expect(sourceText).toMatch(
      /\{\s*user_id:\s*COMMAND_BUS_ACTOR_ID\s*\}/
    );
  });

  it("preserves the remote-auth guard (no user_id in remote mode)", () => {
    // The ternary structure around the spread must remain intact:
    //   ...(runtimeConfig.authMode === "remote" ? {} : { user_id: ... })
    expect(sourceText).toMatch(/authMode\s*===\s*"remote"\s*\?\s*\{\}/);
  });

  it("imports getRuntimeConfigSync from the canonical runtime-config module", () => {
    // Regression: runtimeConfig was undefined because getRuntimeConfigSync
    // was not imported after a refactor removed the import line.
    expect(sourceText).toMatch(/import\s*\{[^}]*getRuntimeConfigSync[^}]*\}\s*from\s*"@\/lib\/runtimeConfig"/);
  });

  it("calls getRuntimeConfigSync before the thread-creation payload", () => {
    // Regression: runtimeConfig.authMode caused ReferenceError because
    // the local const runtimeConfig was never assigned.
    expect(sourceText).toMatch(/const\s+runtimeConfig\s*=\s*getRuntimeConfigSync\(\)/);
  });
});
