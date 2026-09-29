# Parked Lane — Scout Live Continuity Proof

## Current Status

**Not currently assignable to Zac.**

Scout exists as an iOS application shell, but the present product does not provide a usable connection path for a normal tester to connect Scout to a Codexify/Guardian runtime.

The earlier handoff assumed that Zac could configure an operator-approved endpoint and authentication mode from Scout and then execute the first live read in GitHub #815. That assumption is not currently true from the user-facing product.

## Why This Is Parked

A live continuity proof is meaningful only after the app has an actual connection/reachability path that a tester can use without reconstructing developer setup out-of-band.

Right now the missing prerequisite is earlier than the proof:

```
Scout app
  -> usable connection configuration
  -> reachable Guardian/Codexify runtime
  -> explicit authentication
  -> live continuity proof
```

The first arrow is not yet a usable product path.

## Governance Path

Do not ask Zac to repair this casually as part of the collaborator bundle.

Use the governed Codex `/goal` development-operator workflow to recover or define the Scout connection path, keeping product authority with Chris and implementation sequencing inside the existing campaign/governance model.

Once that path exists and is proven usable, this lane can be reactivated and GitHub #815 can again supply the bounded live-continuity proof.

## Reactivation Gate

This lane becomes assignable only when:

- Scout exposes a user-operable way to identify/configure the intended Guardian/Codexify endpoint;
- the supported authentication mode for that endpoint is explicit;
- a tester can establish reachability without founder-only shell/repo knowledge;
- the expected first protected read is defined from current repository truth;
- credentials can be entered and retained through the intended secure path.

Until then, report Scout connection-path observations to Chris and stop. Do not weaken auth, bypass infrastructure, or invent a parallel connection mechanism just to make the old proof script executable.
