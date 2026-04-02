Product Spec — Persona Studio (Agent Command Center)

1. Overview

Persona Studio is a non-conversational configuration and observability interface for defining, editing, and validating agent profiles.

It allows users to configure:

Model behavior (temperature, sampling)
Voice system
Persona/system prompt
Tools, skills, and permissions
Retrieval and memory policies

Profiles created in Persona Studio are saved as reusable runtime presets.

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
Only saved profile configs affect runtime
3. Core Entities
3.1 PersonaProfile
type PersonaProfile = {
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
    version: number
  }
}
3.2 Studio-Only Entities
type ProfileDraft = PersonaProfile & {
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
Export JSON
Import JSON
Reset to last saved
Revert section
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
Output
result payload
debug events
logs in diagnostics panel
6. Runtime Integration
6.1 Profile Application Flow
User selects persona in runtime
System loads PersonaProfile
ContextBroker assembles context
ModelRouter selects provider/model
CommandBus resolves tools
Execution proceeds with:
preconfigured model params
prompt
permissions
retrieval behavior
6.2 Strict Isolation

Persona Studio must never:

write to memory stores
modify thread history
inject into runtime context
create conversation records
7. Observability Requirements
7.1 Effective Config View
Fully resolved profile
Defaults + overrides applied
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
“Ready” badge when valid
Disabled runtime use if invalid
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

Persona Studio is complete when:

Profiles can be created, edited, saved, and loaded
Runtime correctly applies all profile parameters
No memory or chat artifacts are created from Studio usage
Validation prevents invalid runtime states
Diagnostics accurately reflect resolved configuration
Users can reliably switch personas with deterministic behavior
