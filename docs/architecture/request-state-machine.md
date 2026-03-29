## Core design principle

Do **not** model this as:

* healthy / unhealthy
* sent / failed

That binary is too crude for local inference.

Model it as two separate machines:

1. **Provider / runtime state**
2. **Per-message request state**

That separation is the hinge. Without it, one slow load turns into fake “offline,” and one timed-out request turns into a ghost reply.

---

# 1. Provider state machine

This describes the model provider itself, independent of any one message.

## Provider states

```text
OFFLINE
CONNECTING
RUNTIME_AVAILABLE
MODEL_WARMING

READY
GENERATING
DEGRADED
ERROR
```

## Meaning

### `OFFLINE`

* endpoint unreachable
* process not running
* connection refused
* repeated probe failure over threshold

### `CONNECTING`

* initial probe in progress
* transport being checked

### `RUNTIME_AVAILABLE`

* backend process reachable
* API responds
* selected model may still be unloaded

### `MODEL_WARMING`

* backend is alive
* selected model is loading weights, allocating memory, compiling kernels, or otherwise not ready to emit tokens yet

### `READY`

* backend reachable
* selected model ready to accept inference

### `GENERATING`

* at least one active request is streaming or being processed

### `DEGRADED`

* runtime is alive, but one or more signals are poor:

  * unusually high warmup latency
  * queue backed up
  * memory pressure
  * repeated first-token timeout
  * partial stream failures

### `ERROR`

* provider responded with a hard internal error
* not necessarily offline, but currently unreliable

---

## Provider transitions

```text
OFFLINE -> CONNECTING
CONNECTING -> RUNTIME_AVAILABLE
CONNECTING -> OFFLINE

RUNTIME_AVAILABLE -> MODEL_WARMING
RUNTIME_AVAILABLE -> READY
RUNTIME_AVAILABLE -> ERROR

MODEL_WARMING -> READY
MODEL_WARMING -> DEGRADED
MODEL_WARMING -> ERROR

READY -> GENERATING
READY -> DEGRADED
READY -> ERROR
READY -> OFFLINE

GENERATING -> READY
GENERATING -> DEGRADED
GENERATING -> ERROR

DEGRADED -> READY
DEGRADED -> OFFLINE
DEGRADED -> ERROR

ERROR -> CONNECTING
ERROR -> OFFLINE
```

---

# 2. Per-message request state machine

This is the important one. Each user message gets its own request object.

## Request states

```text
DRAFT
QUEUED
DISPATCHING
AWAITING_ACK
AWAITING_MODEL
AWAITING_FIRST_TOKEN
STREAMING
COMPLETED
CANCELLED
TIMED_OUT
FAILED_RETRYABLE
FAILED_FATAL
ORPHANED
REPLAYED
```

## Meaning

### `DRAFT`

* message exists only in composer

### `QUEUED`

* user hit send
* message has local ID
* waiting for dispatch

### `DISPATCHING`

* client is opening request to backend

### `AWAITING_ACK`

* request sent
* waiting for server acknowledgement that it accepted the request

### `AWAITING_MODEL`

* backend acknowledged request
* model is not ready yet
* weight load / queue / warmup in progress

### `AWAITING_FIRST_TOKEN`

* model accepted work
* waiting for first streamed token or first response chunk

### `STREAMING`

* tokens arriving

### `COMPLETED`

* final chunk received and persisted

### `CANCELLED`

* user explicitly stopped it

### `TIMED_OUT`

* request exceeded policy deadline
* not yet known whether backend still completed later

### `FAILED_RETRYABLE`

* transient failure:

  * timeout
  * gateway hiccup
  * provider temporarily overloaded
  * transport interruption

### `FAILED_FATAL`

* invalid request
* unsupported model
* malformed payload
* repeated unrecoverable backend error

### `ORPHANED`

* backend may still be running or may have completed
* client lost stream or detached from request
* request outcome uncertain

### `REPLAYED`

* request was intentionally reissued using same logical message after prior non-final state

---

# 3. The critical rule: message identity vs request identity

You need **two IDs**.

## Message identity

Represents the user’s authored turn.

```ts
messageId
```

This never changes.

## Request identity

Represents an attempt to fulfill that message.

```ts
requestId
attemptNumber
```

This changes per retry or replay.

### Example

```text
messageId = msg_1027
requestId = req_a1   attempt 1
requestId = req_a2   attempt 2
```

That prevents haunted behavior.

Without this split, the UI cannot tell:

* “same message, retried”
  from
* “new message, new turn”

---

# 4. Recommended request object

```ts
type RequestStatus =
  | 'QUEUED'
  | 'DISPATCHING'
  | 'AWAITING_ACK'
  | 'AWAITING_MODEL'
  | 'AWAITING_FIRST_TOKEN'
  | 'STREAMING'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'TIMED_OUT'
  | 'FAILED_RETRYABLE'
  | 'FAILED_FATAL'
  | 'ORPHANED'
  | 'REPLAYED';

interface ChatMessage {
  messageId: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  logicalState: 'draft' | 'submitted' | 'answered' | 'unanswered';
}

interface InferenceAttempt {
  requestId: string;
  messageId: string;
  attemptNumber: number;
  provider: string;
  model: string;
  status: RequestStatus;

  queuedAt?: string;
  dispatchedAt?: string;
  ackAt?: string;
  modelAcceptedAt?: string;
  firstTokenAt?: string;
  completedAt?: string;
  cancelledAt?: string;
  timedOutAt?: string;
  failedAt?: string;

  errorCode?: string;
  errorMessage?: string;

  tokenCountIn?: number;
  tokenCountOut?: number;

  wasReplay: boolean;
  replayOfRequestId?: string;

  backendJobId?: string;
  streamId?: string;
}
```

---

# 5. The timers must be separate

This is where a lot of systems quietly stab themselves.

## Use four clocks, not one

### A. Transport timeout

“How long do I wait to connect to the backend at all?”

Example:

* 2s to 5s local

Triggers:

* connection refused
* DNS failure
* socket open failure

This can justify `OFFLINE`.

---

### B. Ack timeout

“How long do I wait for the backend to acknowledge receipt of the request?”

Example:

* 3s to 10s

If missed:

* request may not have been accepted
* move to `FAILED_RETRYABLE` or `ORPHANED` depending on transport evidence

---

### C. Model readiness timeout

“How long do I allow the model to warm or queue before I call this delayed?”

Example:

* 30s to 180s for large local models

If exceeded:

* **do not call provider offline**
* set provider `DEGRADED`
* set request `AWAITING_MODEL` with delayed UX
* optionally offer retry/cancel

This is the missing distinction in your current system.

---

### D. First-token timeout

“How long after model acceptance do I expect first output?”

Example:

* 10s to 45s depending on model size

If missed:

* request becomes `TIMED_OUT` or `ORPHANED`
* provider maybe `DEGRADED`
* not automatically `OFFLINE`

---

# 6. Recommended UX mappings

## Bad current mapping

* no quick 200
* banner: **LLM backend offline**

That is too absolute.

## Better mapping

### `CONNECTING`

> Checking model runtime...

### `RUNTIME_AVAILABLE`

> Runtime reachable.

### `MODEL_WARMING`

> Loading selected model into memory...

### `DEGRADED`

> Model is responding slowly.

### `AWAITING_MODEL`

> Your request is queued while the model warms up.

### `AWAITING_FIRST_TOKEN`

> Model is preparing a response...

### `ORPHANED`

> Response state is uncertain. You can wait, retry, or recover the last attempt.

### `OFFLINE`

> The model runtime is unreachable.

That distinction will save you a lot of false error perception.

---

# 7. Preventing ghost replies

This is the part that matters most for transcript integrity.

## Rule

A user message should not become “answered” until a specific attempt reaches `COMPLETED`.

## Never do this

* append user turn permanently
* let request timeout ambiguously
* send next message with the same unresolved turn without marking replay

That creates transcript drift.

## Better model

Each user turn can be in one of these logical states:

```text
submitted_unanswered
answered
abandoned
replayed
```

If message A times out, keep it explicitly marked:

> “Message A has not yet received a confirmed response.”

Then when user sends message B, you have choices:

### Option 1. Block

Require the user to resolve A first.

Too rigid for chat UX.

### Option 2. Soft merge

Prompt:

> “Previous message is still unresolved. Retry it, cancel it, or continue anyway?”

Good for careful workflows.

### Option 3. Automatic replay with explicit marker

When sending B:

* either replay A intentionally
* or omit A from model input if user chose to continue without retry

But this must be explicit in state, not accidental.

---

# 8. Recommended reconciliation logic

When a request times out, you need a cleanup job.

## Reconciliation states

### If backend later confirms completion for timed-out request

* mark attempt `COMPLETED_LATE` or just `COMPLETED`
* attach response to original `messageId`
* show subtle note:

  * “Previous response arrived after timeout.”

### If next request is sent before resolution

* do not silently reuse unresolved attempt
* create new attempt:

  * `requestId = req_a2`
  * `wasReplay = true`
  * `replayOfRequestId = req_a1`

### If server never confirms prior attempt

* mark old attempt `ORPHANED`
* preserve audit trail

---

# 9. Concrete event flow for your exact bug

Here is the likely path in your system now:

```text
User sends message
-> UI creates pending message
-> Client dispatches request
-> Backend is busy loading weights
-> Health probe times out
-> Provider marked llm_unhealthy
-> Banner says backend offline
-> Request is either:
   a) still running
   b) dropped by client
   c) unresolved but message remains in transcript
-> User sends next message
-> Full history is resent
-> Model answers old unresolved turn
-> UI looks haunted
```

## Corrected version

```text
User sends message
-> messageId created
-> requestId created
-> request status = QUEUED
-> dispatch starts
-> backend reachable
-> provider = RUNTIME_AVAILABLE
-> backend says model loading
-> provider = MODEL_WARMING
-> request = AWAITING_MODEL
-> UI shows "Loading selected model..."
-> first token arrives
-> request = STREAMING
-> provider = GENERATING
-> completion finishes
-> request = COMPLETED
-> provider = READY
```

If model takes too long:

```text
-> request remains AWAITING_MODEL
-> provider = DEGRADED
-> UI shows delayed state, not offline
-> user may wait, cancel, or retry
```

---

# 10. Minimal implementation contract

If you only implement five things, make them these:

## 1. Split provider health from request health

Provider health is global.
Request health is per-turn.

## 2. Add `MODEL_WARMING`

This is probably the missing state.

## 3. Add `messageId` and `requestId`

One message can have multiple attempts.

## 4. Track `AWAITING_MODEL` separately from `OFFLINE`

Cold start is not offline.

## 5. Never silently replay unresolved turns

If replay happens, mark it as replay.

---

# 11. Suggested reducer / state transitions

A compact reducer shape:

```ts
type ProviderState =
  | 'OFFLINE'
  | 'CONNECTING'
  | 'RUNTIME_AVAILABLE'
  | 'MODEL_WARMING'
  | 'READY'
  | 'GENERATING'
  | 'DEGRADED'
  | 'ERROR';

type RequestState =
  | 'QUEUED'
  | 'DISPATCHING'
  | 'AWAITING_ACK'
  | 'AWAITING_MODEL'
  | 'AWAITING_FIRST_TOKEN'
  | 'STREAMING'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'TIMED_OUT'
  | 'FAILED_RETRYABLE'
  | 'FAILED_FATAL'
  | 'ORPHANED'
  | 'REPLAYED';
```

Example transition handlers:

```ts
onSendMessage -> QUEUED
onDispatchStart -> DISPATCHING
onAckReceived -> AWAITING_MODEL | AWAITING_FIRST_TOKEN
onModelLoading -> AWAITING_MODEL
onFirstToken -> STREAMING
onStreamComplete -> COMPLETED
onUserCancel -> CANCELLED
onRequestTimeout -> TIMED_OUT
onDisconnectAfterAck -> ORPHANED
onRetry -> REPLAYED + new attempt QUEUED
```

Provider side:

```ts
onProbeStart -> CONNECTING
onRuntimeReachable -> RUNTIME_AVAILABLE
onModelLoadNotice -> MODEL_WARMING
onReady -> READY
onGenerationStart -> GENERATING
onLatencySpike -> DEGRADED
onHardConnectionFailure -> OFFLINE
onBackend500 -> ERROR
```

---

# 12. Observability fields you absolutely want

For each attempt, log:

```text
conversation_id
message_id
request_id
attempt_number
provider
model
client_send_ts
server_ack_ts
model_load_start_ts
model_ready_ts
first_token_ts
stream_end_ts
timeout_ts
cancel_ts
disconnect_ts
final_status
backend_job_id
```

And compute:

```text
transport_latency
ack_latency
model_warmup_latency
first_token_latency
total_completion_latency
```

That will turn debugging from séance to engineering.

---

# 13. The product-level UX you probably want

For local inference, I’d present these states:

### While loading weights

> **Loading model**
> The selected model is being loaded into memory. This can take a moment.

### While waiting for first token

> **Preparing response**
> The runtime is connected, but the model has not started streaming yet.

### On degraded latency

> **Response delayed**
> The model is available, but startup is slower than usual.

### On real offline

> **Runtime offline**
> Codexify cannot reach the selected model provider.

That language is much more truthful.

---

# 14. My practical diagnosis

Your guess is probably right in spirit:

* **timeout classification is too aggressive**
* **cold-start latency is being treated as runtime failure**
* **message/request identity is probably not separated enough**
* **subsequent sends may be replaying unresolved history without explicit state**

So the fix is not just “increase timeout.”
That helps, but it is only paint on the wall.

The real fix is:

* richer provider states
* richer request states
* explicit replay semantics
* late-result reconciliation

That gives Codexify a memory of what actually happened instead of forcing it into a false yes/no.