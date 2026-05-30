# Canonical Tokens

Codexify uses canonical tokens to keep repeated meaning from drifting across code, docs, logs, and UI.

## The Rule

When a literal carries contract meaning and starts repeating, it should become a canonical token.

## Two Token Families

- UI tokens govern visual truth.
- protocol and domain tokens govern semantic truth.

That distinction is important because a surface can look consistent while its runtime meaning is still drifting.

## What Should Become Canonical

Repeated literals should be promoted when they represent:

- statuses
- event names
- error codes
- lifecycle states
- release posture labels

## Why It Matters

The same token may appear in routes, workers, logs, tests, and docs.
If each layer invents its own synonym, operators lose the ability to read the system consistently.

Canonical tokens keep the runtime grep-friendly and reduce ambiguity during incident response, release review, and UI interpretation.
