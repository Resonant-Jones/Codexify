# Identity and Personas

Codexify treats identity as explicit, owned, and bounded.

## Core Doctrine

- chat history is content, not durable identity by default
- deep identity is opt-in
- personas borrow identity; they do not own it
- Persona Studio is configuration, not conversation

## What That Means

Identity should not be silently inferred from the mere existence of a conversation trail.
Persona configuration can shape behavior, but it does not redefine ownership of durable user identity.

## Persona Studio Boundary

Persona Studio exists as a profile and configuration surface.
It is not a chat transcript surface, and it does not become the authority on identity simply because it can change model or tool settings.

## Safety Boundary

Do not infer sensitive traits from conversation history unless an explicit, governed feature says otherwise.

The doctrine here is about minimizing accidental identity contamination while keeping the runtime useful.
