Product Spec — Persona Studio (Agent Command Center)

## Architecture status

[ADR-082: Persona Profile Manifest and Binding Authority](./adr/082-persona-profile-manifest-and-binding-authority.md)
governs Persona Studio persistence and authority semantics. The canonical
authored object is the typed PersonaProfileManifest; YAML and JSON are
serialization formats only. Browser localStorage and a database JSON blob are
not authority sources.

PersonaProfileManifest records requested configuration. A separate,
server-owned PersonaProfileBinding owns account, Project, participant,
connection, activation, and environment-specific authority. A profile import
cannot self-assign those bindings, credentials, or execution permission.

Current code-path scope is deliberately narrower: the Studio maintains a broad
browser-local draft, while backend persistence and system-profile resolution
currently carry only name, system prompt, model provider, model ID, and
temperature. Broader fields below describe authored intent and future
implementation direction; they do not claim current runtime enforcement or
release support.

1. Overview

Persona Studio is a non-conversational configuration and observability interface for defining, editing, and validating agent profiles.

It allows users to configure:

Model behavior (temperature, sampling)
Voice system
Persona/system prompt
Tools, skills, and permissions
Retrieval and memory policies

Profiles may be represented as reusable runtime presets only through
separately implemented persistence and binding seams. Saving a profile is not
runtime execution or an authority grant.

Persona Studio itself:

does not maintain chat history
does not write to memory systems
does not act as a conversational interface
2. Core Principles
2.1 Separation of Concerns
Persona Studio = configuration layer
Runtime Chat = execution layer
Memory = external system (thread/project/workspace)
2.2 Stateless Interaction
No conversation objects
No message persistence
Only config state + validation/test outputs
2.3 Deterministic Output
Profiles must produce predictable runtime behavior
All derived config must be inspectable
2.4 No Identity Contamination
Studio actions do not modify persona memory or identity
Saving, validating, importing, or exporting a profile does not write memory,
infer durable traits, or execute runtime behavior
2.5 Manifest and Binding Separation
PersonaProfileManifest owns authored intent
PersonaProfileBinding is server-owned environmental authority
Requested configuration is not effective configuration
3. Core Entities
3.1 PersonaProfileManifest (conceptual)

This product inventory is a conceptual typed shape, not
implementation-language-specific field syntax. ADR-082 is the authoritative
manifest contract.

type PersonaProfileManifest = {
  id: string
  name: string
  description?: string
  avatar?: string

  model: {
    provider: string
    modelId: string
    temperature: number
    topK?: number
    topP?: number
    maxTokens?: number
  }

  voice: {
    enabled: boolean
    provider?: string
    voiceId?: string
    speed?: number
    style?: string
    wakeWord?: string
    interruptible?: boolean
  }

  prompt: {
    systemPrompt: string
    styleNotes?: string
    directives?: string
  }

  tools: {
    pinned: string[]
    allowed: string[]
    skills: string[]
  }

  permissions: {
    web: boolean
    filesystem: "none" | "scoped" | "full"
    email: boolean
    calendar: boolean
    automation: boolean
    cli: boolean
  }

  retrieval: {
    enabled: boolean
    mode: "off" | "thread" | "project" | "workspace"
    topK: number
    scoreThreshold?: number
    rerank: boolean
  }

  runtimeFlags: {
    interruptibleVoice: boolean
    showTrace: boolean
    verboseLogs: boolean
    safeMode: boolean
  }

  metadata: {
    createdAt: string
    updatedAt: string
    apiVersion: string
    revision: string
  }
}

The stable profile identity and the revision are distinct. apiVersion
describes manifest-schema compatibility; revision identifies one immutable
authored configuration snapshot. A mutable version number that points only at
current state is not enough for future thread-to-profile-revision binding.

The model, voice, tool, skill, permission, retrieval, and connector-shaped
fields above are requests or declared ceilings. They do not by themselves
grant capability, connector, Project, participant, credential, retrieval, or
voice authority. Connector references, when present, are non-secret logical
aliases only; no OAuth token, API key, password, provider credential, session
credential, or connection secret belongs in the manifest.

3.2 PersonaProfileBinding (server-owned conceptual envelope)

The server separately owns the binding for a manifest or revision. It contains
the authoritative account owner, permitted Project bindings, participant or
contact policy, connection-resolution mappings, activation state, and
environment-specific reference mappings. Imported YAML or JSON must be
validated, remapped, approved, or rejected against those server-owned
controls; it cannot choose them.

3.3 Studio-Only Entities
type ProfileDraft = PersonaProfileManifest & {
  isDirty: boolean
  validationState: "valid" | "warning" | "invalid"
}

type ProfileValidationEvent = {
  type: "error" | "warning"
  field: string
  message: string
}

type ProfileTestRun = {
  id: string
  type: "voice" | "prompt" | "retrieval" | "tools"
  result: any
  timestamp: string
}

type ProfileDebugEvent = {
  event: string
  payload?: any
  timestamp: string
}
4. User Experience
4.1 Layout
Left Panel — Profile Manager
List of profiles
Search/filter
Create new
Duplicate
Delete
Import / export
Default selector
Main Panel — Profile Editor

The editor may show Project, participant, connector, capability, retrieval, or
voice requests, but it must label them as requested until a server-owned
binding and the owning resolver establish an effective configuration. The
editor must not treat configuration presence as connector authorization,
connector authorization as health, or provider selection as model
availability.

Tabbed interface:

1. Identity
Name
Description
Avatar / color
Base template
2. Model
Provider
Model selection
Temperature
Top K (generation)
Top P
Max tokens
Fallback model
3. Voice
Enable / disable
Provider
Voice preset / clone
Speed
Style
Wake word
Interruptible speech
4. Prompt
System prompt (primary field)
Style notes
Directives
Guardrails
5. Tools
Pinned tools
Allowed tools
Skills attached
Tool priority
6. Permissions
Web access
File system scope
Email
Calendar
CLI
Automation
7. Retrieval
Enabled toggle
Mode (thread/project/workspace)
Retrieval Top K
Score threshold
Reranking toggle
8. Observability
Effective config preview
Resolved prompt preview
Permission matrix
Validation results
Right Panel — Diagnostics
Sections
Save status
Validation output
Config diff
Last test run
Debug event stream
Effective runtime snapshot
9. Key Functional Behavior
5.1 Save Model

Actions:

Save
Save as new
Duplicate
Export JSON or YAML (future, non-secret serialization)
Import JSON or YAML (future, server-validated)
Reset to last saved
Revert section

An import/export feature must serialize PersonaProfileManifest only. It must
not serialize credentials, create account ownership, bind Projects or
participants, grant connector access, or grant execution authority. Until a
full-manifest persistence task is implemented, the current saved runtime seam
remains limited to name, system prompt, model provider, model ID, and
temperature.
5.2 Validation System

Triggered on:

field change
save attempt

Validations include:

missing required fields
incompatible model params
unavailable providers
tool-permission conflicts
retrieval enabled without sources

Validation distinguishes manifest shape from environment authority. A selected
provider is not proof of inventory availability; a configured connection is
not authorization or health; and a valid requested capability is not an
effective capability.
5.3 Test System (Non-Persistent)
Test Types
Test Voice
Test Prompt
Test Retrieval
Test Tools
Constraints
no memory writes
no chat history creation
no persona mutation
no authority grant or execution merely from validation
Output
result payload
debug events
logs in diagnostics panel
6. Runtime Integration and Execution Boundary

6.1 Current Compatible Projection

The existing runtime-bearing persistence seam can project only:

name
system prompt
model provider
model ID
temperature

A future manifest-persistence implementation may project those five values
through the existing system-profile resolver. It does not require a wholesale
resolver rewrite. The remaining manifest fields stay non-executing until each
has a separately implemented, authorized, and proven enforcement seam.

6.2 Requested Versus Effective Application

The intended profile-application path is not a direct UI-to-runtime pipe:

1. PersonaProfileManifest records requested configuration.
2. PersonaProfileBinding supplies server-owned account, Project,
   participant, connection, activation, and environmental scope.
3. The owning systems determine resource availability and policy denials.
4. The existing effective capability resolver supplies the capability snapshot
   with its unchanged profile > Project > account precedence.
5. Applicable runtime and support policy determines the narrow effective
   configuration that may reach a runtime.

For capabilities:

effective capabilities =
profile requested ceiling
intersection resolved capability snapshot(account, project, profile)
intersection applicable runtime/support policy

No effective-configuration endpoint or full resolver exists today; a future
view remains observational until a runtime-integration task explicitly
authorizes execution.

6.3 Strict Isolation

Persona Studio must never, merely by editing, saving, importing, exporting,
validating, or inspecting a profile:

write to memory stores
modify thread history
create conversation records
invoke a model
execute a tool or capability
perform retrieval
invoke a connector
change provider health
grant new authority

7. Observability Requirements
7.1 Effective Config View
Requested configuration
Available configuration
Denied configuration with reason
Effective configuration
Capability-resolution source and scope
Connection setup, authorization, and health shown separately
7.2 Prompt Preview
Final compiled system prompt
7.3 Event Log

Examples:

profile.loaded
field.changed
config.validated
config.saved
test.started
test.completed
permission.denied
provider.unavailable
7.4 Diff Viewer
Compare draft vs saved profile
Highlight modified fields
8. Critical UX Rules
8.1 No Chat UI
No message bubbles
No conversation threading
No assistant persona presence
8.2 Explicit Parameter Separation

Clearly distinguish:

Generation Top K (model sampling)
Retrieval Top K (memory fetch)
8.3 Runtime Readiness Indicator
Show manifest validity separately from effective runtime eligibility
Do not label a selected provider, configured connector, or requested capability
as ready without the owning availability, authorization, health, and
runtime/support-policy evidence
8.4 Unsaved State Visibility
Persistent unsaved indicator
Section-level dirty state
9. Non-Goals

Persona Studio will NOT:

act as a chat interface
store conversations
manage long-term memory
simulate runtime threads
mutate persona identity directly
10. Future Extensions (Optional)
Template marketplace (prebuilt personas)
Version history / rollback
Profile inheritance system
Sharing/export registry
Multi-profile A/B comparison
Live runtime telemetry hook
11. Naming
Feature: Agent Command Center
Primary workspace: Persona Studio
Internal modules:
Profile Editor
Runtime Preview
Diagnostics
12. Definition of Done

The architecture contract is complete when:

PersonaProfileManifest and PersonaProfileBinding remain distinct
API schema compatibility and immutable profile revision semantics remain
distinct
Imports cannot self-grant environmental authority or include secrets
The five-field compatible projection remains explicit until broader
enforcement seams are proven
No memory, chat, identity, connector, retrieval, tool, capability, or model
execution is inferred from Studio save or validation behavior
Diagnostics distinguish requested, available, denied, and effective
configuration

A future implementation may declare an individual runtime field complete only
when its owning binding, authorization, enforcement, and proof seams are
implemented. This specification does not claim that all displayed profile
parameters currently apply at runtime.
