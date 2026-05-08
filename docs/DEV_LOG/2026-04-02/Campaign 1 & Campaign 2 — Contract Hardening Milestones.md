# **Dev Log - 2026-04-02**

## **Summary**


Today was a contract-hardening day.

Campaign 1 and Campaign 2 tightened the two most important seams in the chat runtime:

- **thread-level execution identity**
    
- **turn-level response identity**
    

  
Together, they moved Codexify further away from ambient, drifting behavior and closer to explicit runtime truth. Thread configuration is now treated as durable state instead of soft UI preference, and completion targeting now follows the latest accepted user turn instead of relying on loose conversational inference. That aligns with the broader runtime direction already documented in the current architecture KB: queue-backed execution, explicit acceptance semantics, and contract-driven truth surfaces.   

---

## **What I completed**

  ### **Campaign 1 — Thread configuration hardening**

I finished the thread-config pass so chat selector choices now belong to the thread itself instead of floating as unstable client-side state.

That work included:

- adding a narrow updateThreadConfig(threadId, patch) API helper
    
- introducing a shared ThreadConfig type
    
- hydrating active thread selector state from persisted thread_config
    
- persisting provider / model / inference / retrieval selector changes back through the thread config PATCH path
    
- preserving draft behavior before a thread exists, then reconciling to durable config once the thread is created
    
- preserving thread_config across canonical backend read surfaces
    
- restoring thread_config through frontend sidebar hydration and active-thread restoration
    

This mattered because the system already treats threads as the primary conversation container and relies on durable thread/message state in Postgres. Campaign 1 extended that truth to execution settings as well. A thread now carries more of its own behavioral contract.

---

### **Campaign 2 — Latest-turn targeting hardening**

  

I finished the completion-seam work that makes the runtime respond to the correct user turn explicitly.

  

That work included:

- splitting completion assembly into:
    
    - history
        
    - latest_turn
        
    - retrieved_context
        
    
- adding a dedicated latest-turn-only system instruction to the provider-ready prompt
    
- ensuring retrieval query derivation uses the newest user turn explicitly
    
- surfacing latest-turn targeting in the internal completion seam
    
- exposing latest-turn targeting in the public trace seam
    
- carrying latest_turn_message_id from route acceptance into the queued task payload
    
- honoring that explicit target in worker execution so the worker does not drift if the thread changes before the task runs
    

  
This lines up with the runtime’s documented distinction between acceptance, execution, and visibility. The queue path already made it clear that acceptance is not completion. Campaign 2 adds the missing precision around **what** accepted work is actually supposed to answer.

---

## **Important outcome**

  
The biggest shift today:

**A thread now has a durable execution identity.**

And:

**A completion now has a durable response target.**

That means two major ambiguity classes got reduced:

- selector drift across reloads, hydration paths, and thread restoration
    
- response drift across multi-turn conversations and queue delay windows
    

The system already had a strong bias toward canonical runtime truth surfaces and explicit protocol tokens. These two campaigns pushed that philosophy deeper into the actual chat loop.

---
## **Campaign 1 commits**

- 07cdc37f4 - wired chat selectors to the durable thread config path
    
- 14c47df7b17c65e6e1c7c2b45b1dbe16e58c15fa - preserved thread_config across canonical thread read surfaces
    

---
## **Campaign 2 commits**

- 0a5177f5a27a14237f1f551d02051877043f56c0 - added latest-turn boundary to completion assembly
    
- d745f0a860f5600faaefc4119f845629e2b150ff - implemented latest-turn-only prompt instruction
    
- 98a30d11a7b2aad8631c7d111dd6944e8454dd91 - added latest-turn regression coverage
    
- 0cfb3001fa5356095f2154e09ec07360750912be - hardened retrieval targeting to latest turn
    
- 88e8a29262d512fe3d5c1c27ca8f0483eb1c52e3 - exposed latest-turn targeting in trace seam
    
- c7a73fd67a10130d383e1c8a83abf5ff848a058e - carried latest_turn_message_id through route, queue, and worker execution
    

---

## **Notes**

This was not a feature-glamour pass. It was a **semantic integrity** pass.

Campaign 1 eliminated one kind of “why did the thread forget what it was using?” problem.

Campaign 2 eliminated one kind of “why is the assistant answering the wrong thing?” problem.

Neither campaign makes the product look radically different on first glance. Both make it more trustworthy under the hood, which is the better trade.

Also worth noting: this work lands cleanly inside the current beta-readiness frame. The supported path is still local Docker Compose with a queue-backed chat loop, and the current release truth still depends on explicit evidence, not vibes. These campaigns strengthen that evidence model instead of bypassing it. 

---
## **Next likely moves**

### **After Campaign 1**

- expand thread config into a broader thread-behavior contract where appropriate
    
- keep read/write surfaces aligned so config never falls off the hydration path again
    

### **After Campaign 2**

- continue strengthening transcript integrity and replay safety
    
- align runtime state presentation more tightly with actual request identity and provider lifecycle semantics
    
- keep trace truth and execution truth bound together
    

---
## **Closing thought**

Today was a systems honesty day.

The chat loop now knows more clearly:

- what a thread is configured to do
    
- what a completion is supposed to answer
    

That sounds small until you remember how many strange behaviors are born from those two things being fuzzy.

---
# **Founder’s Narrative Log - 2026-04-02**

Today was less about adding magic and more about removing ghosts.

Not ghosts in the dramatic sense. Runtime ghosts. The kind that show up when a thread quietly forgets which model it was using, or when a queued completion answers the wrong user turn because the conversation moved while the worker was still catching up. The kind of ghosts that make software feel haunted when it is really just under-specified.

So this was a day for specification.
## **Campaign 1**

The first campaign locked thread behavior to the thread itself.

That sounds obvious in retrospect, which is usually how you know it mattered.

Provider, model, inference mode, retrieval mode, all of that was too vulnerable to drifting between local draft state, defaults, hydration paths, and whatever the frontend happened to remember at the moment. It worked often enough to feel close, but not enough to deserve trust. So I moved it onto the durable thread-config path and then kept following it until the read surfaces stopped dropping it.

That changed the shape of the system a little.

A thread is no longer just a container full of messages. It carries more of its own execution identity now.

That is healthier.
## **Campaign 2**

The second campaign was about response targeting.

This one goes straight to the spine.

A chat system cannot afford to be vague about what it is answering. Not if it has queues. Not if it has workers. Not if it has real delay windows between acceptance and execution. Not if transcript integrity matters.

So I split the completion seam into history, latest_turn, and retrieved context. Then I forced the prompt to acknowledge the rule directly: prior messages are context, the newest user message is the response target. Then I followed that all the way through retrieval, traces, queued task payloads, and worker execution.

That last part matters most.

Because it is not enough for the route layer to know what the latest turn was when it accepted the work. The worker has to know what it is there to answer even if the thread changes before execution.

Otherwise you are not building a conversation system. You are building a probability field with UI.

## **What changed, really**

On paper, these campaigns look like persistence work, assembly work, trace work, queue work.

And yes, they are those things.

But the deeper change is that Codexify got more explicit about identity at two levels:

- the identity of the thread as an execution surface
    
- the identity of the turn as the response target
    

That is the real throughline.

Campaign 1 gave the thread a stronger memory of how it should behave.

Campaign 2 gave the completion a stronger memory of what it owes an answer to.

The runtime is a little less ambient now. A little less willing to improvise meaning out of loose context. That is good. Improvisation is charming in music and terrible in state machines.
## **Why this matters**

A lot of bad software behavior is not dramatic failure. It is soft dishonesty.

The model selector looks set, but the backend answers with something else.

The thread appears stable, but rehydration quietly reverts it.

The assistant replies coherently, but to the wrong turn.

Nothing crashes. Nothing burns. But truth gets blurry.

That blur is expensive.

These two campaigns were about reducing that blur.

## **Commits**

### **Campaign 1**

- 07cdc37f4 - wired chat selectors to the durable thread config path
    
- 14c47df7b17c65e6e1c7c2b45b1dbe16e58c15fa - preserved thread_config across canonical thread read surfaces
    
### **Campaign 2**

- 0a5177f5a27a14237f1f551d02051877043f56c0 - added latest-turn boundary to completion assembly
    
- d745f0a860f5600faaefc4119f845629e2b150ff - implemented latest-turn-only prompt instruction
    
- 98a30d11a7b2aad8631c7d111dd6944e8454dd91 - added latest-turn regression coverage
    
- 0cfb3001fa5356095f2154e09ec07360750912be - hardened retrieval targeting to latest turn
    
- 88e8a29262d512fe3d5c1c27ca8f0483eb1c52e3 - exposed latest-turn targeting in trace seam
    
- c7a73fd67a10130d383e1c8a83abf5ff848a058e - carried latest_turn_message_id through route, queue, and worker execution
    
## **Closing**

Today did not make Codexify louder.

It made it more exact.

And for this stage of the system, exactness is worth more than spectacle. The product is getting closer to a place where it does not merely appear coherent. It can explain why it is coherent, and keep being coherent under pressure. That is a better foundation to build on. 

