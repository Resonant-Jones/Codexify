"""Guardian's native (non-HTTP) command-bus tool family.

A native command is a command-bus command with ``layer="internal"`` that
executes **in process** rather than over the loopback HTTP transport. Native
commands are declared in :mod:`guardian.native_tools.command_specs`, dispatched
through :mod:`guardian.native_tools.dispatch`, and executed by a handler in
:mod:`guardian.native_tools.handlers`.

The family is deliberately small and deliberately read-only. Every command in
it:

* resolves its own authority from the authenticated principal and the Project
  it is scoped to, so a caller cannot widen its own grant by supplying a
  different scope;
* mutates nothing, runs no subprocess, and uses no network;
* bounds its own output, because the tool result is injected into the model's
  context whole.
"""

from __future__ import annotations

__all__ = ["command_specs", "dispatch"]
