# Dev Log — 2026-04-02

## Summary

Today was not a feature day.

It was a **truth alignment day**.

The system already _worked_, but it didn’t always behave in a way that could be trusted. Config drifted. The assistant sometimes answered the wrong thing. And worst of all, the system could be actively working while looking completely dead.

The focus today was fixing those gaps by hardening three layers of the system:

- thread-level execution truth
    
- turn-level response targeting
    
- runtime visibility and streaming
    

---

## What I completed

### Thread contract hardening (Campaign 1)

- introduced `thread_config` as a durable execution contract on `chat_threads`
    
- snapshot config at thread creation so threads inherit defaults once and then become independent
    
- made completion resolve provider/model/inference/retrieval strictly from thread config
    
- added explicit mutation path for thread config instead of relying on UI or request-time overrides
    
- wired frontend selectors to the backend contract
    
- ensured thread config survives all read surfaces and hydration paths
    

---

### Turn boundary hardening (Campaign 2)

- introduced an internal completion structure:
    
    - `history`
        
    - `latest_turn`
        
    - `retrieved_context`
        
- explicitly targeted the most recent user message in prompt assembly
    
- aligned retrieval queries to the latest turn
    
- added regression coverage for multi-turn correctness
    
- exposed target-turn identity in trace
    
- preserved `latest_turn_message_id` across queue → worker → trace
    

---

### Runtime visibility and streaming (Campaign 3)

#### Lifecycle system

- introduced canonical lifecycle states:
    
    - QUEUED
        
    - AWAITING_MODEL
        
    - AWAITING_FIRST_TOKEN
        
    - STREAMING
        
    - COMPLETED
        
- emitted those states from the worker
    
- surfaced them in the frontend chat UI
    

#### Lifecycle stability

- made lifecycle state thread-scoped
    
- eliminated stale state bleed across thread switches
    
- kept waiting states stable under slow local inference
    

#### Timing instrumentation

- added:
    
    - `queued_at`
        
    - `awaiting_model_at`
        
    - `awaiting_first_token_at`
        
    - `first_token_at` / `first_output_at`
        
    - `completed_at`
        
- persisted timings into the trace/evidence path
    

#### Latency UI

- added compact latency readouts:
    
    - warmup time
        
    - first-token time
        
    - total duration
        

#### Streaming

- introduced `task.chunk` events on the existing task-event pipeline
    
- streamed assistant output incrementally in the chat UI
    
- scoped streamed drafts to active thread/task
    
- reconciled streamed drafts with final persisted assistant messages
    
- ensured non-streaming paths remain unchanged
    

---

## Important outcome

The biggest shift today:

**The system no longer hides its work.**

And:

**The system now knows exactly what it is supposed to do, what it is answering, and shows you how it is doing it.**

---

## Commits

- `9ee9fdb9` – add thread_config to chat_threads
    
- `25f0c343` – snapshot thread config at creation
    
- `68747e61` – make thread config authoritative for completion
    
- `0111e5d0` – add thread config mutation route
    
- `07cdc37f4` – wire selectors to thread config
    
- `14c47df7` – preserve thread config across read surfaces
    
- `0a5177f5` – split completion history from latest turn
    
- `d745f0a8` – target only latest user turn in prompts
    
- `98a30d11` – add latest-turn regression coverage
    
- `0cfb3001` – align retrieval to latest turn
    
- `88e8a292` – expose latest-turn targeting in trace
    
- `c7a73fd6` – preserve latest-turn identity across queue
    
- `795bebba` – emit lifecycle events
    
- `d4b9757c` – render lifecycle in UI
    
- `5022ca36` – harden lifecycle timing and cleanup
    
- `50d225f5` – instrument first-output timing
    
- `1966d938` – add latency readouts in UI
    
- `cd8769d9` – stream assistant chunks over task events
    

---

## Notes

One important observation:

The system didn’t need new features to improve. It needed **contracts to stop drifting**.

Today’s work was largely about removing silent failure modes:

- config falling back without warning
    
- responses targeting multiple turns
    
- execution happening without visibility
    

Fixing those revealed how much of the system was already correct, just not enforced.

---

## Next likely moves

### Observability

- unify lifecycle, timing, and trace into a single diagnostics surface
    
- make operator truth easier to inspect without digging
    

### Product layer

- build on top of stable contracts:
    
    - personas
        
    - workflows
        
    - automations
        

---

## Closing thought

Today didn’t make the system more powerful.

It made it **more honest**.

And that changes how everything else gets built.




# Narrative Log

# Dev Log — 2026-04-02

Today was not about building something new.

It was about making the system stop contradicting itself.

---

There were three problems sitting underneath everything:

The first was quiet.

The system didn’t always remember how it was supposed to behave. Models would reset. Providers would drift. A thread didn’t actually _own_ its execution. It borrowed it from whatever the environment happened to be at that moment.

The second problem was louder.

The assistant didn’t always know what it was answering. It would treat the conversation like a pile of open tasks instead of a sequence. Sometimes it answered the newest message. Sometimes it stitched together answers to several older ones. It looked like intelligence, but it was really ambiguity.

The third problem was the most frustrating.

You could send a message, and the system would go completely silent. No signal. No feedback. Then, after a while, everything would appear at once. The system was working, but it looked dead.

---

So the work today followed those three threads.

### First, the thread itself

I gave the thread a spine.

Instead of letting execution settings float, I anchored them directly to the thread. Model, provider, inference mode, retrieval source. All of it now lives in one place, persists, and can be changed explicitly.

A thread stopped being a suggestion.

It became a container.

---

### Then, the turn

I gave the system a target.

I split the conversation into history and the latest turn. Not conceptually. Structurally. The system now knows which message it is answering, and everything else is just context.

Prompting follows that. Retrieval follows that. The queue carries that identity all the way into execution. And the trace shows it.

The system stopped guessing what to respond to.

---

### Then, the silence

I gave the system a pulse.

Instead of waiting for the final answer, the system now exposes what it’s doing:

Queued.  
Warming model.  
Waiting for first token.  
Generating.

And it doesn’t just show states. It shows time. How long it spent warming. How long until the first token. How long the whole thing took.

And finally, it started talking while it was thinking.

Streaming came through the same pipeline the system was already using. No new channel. No workaround. Just letting the existing path carry real content instead of only terminal results.

---

## What changed today, really

Three things became true:

- The system knows how it should behave
    
- The system knows what it is answering
    
- The system shows what it is doing
    

That sounds simple. It isn’t.

Most systems fake at least one of those.

---

## Personal note

There’s a point where a system stops feeling unpredictable.

Not because every bug is gone, but because the structure underneath stops fighting itself.

Today felt like crossing that line.

---

## What comes next

Now that the system is stable at its core:

Either we make it **deeply observable**,  
or we start building **differentiation on top of something that doesn’t lie**.

Both are finally possible.

---

## Closing

Nothing flashy happened today.

But something important did.

The system became negotiable.

And that’s where real building begins.