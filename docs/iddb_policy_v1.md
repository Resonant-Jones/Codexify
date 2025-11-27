# Identity Data Database (IDDB) Policy v1

Codexify is a local-first thinking companion. It runs on your machine, against your data, with your consent. This document describes how identity-related data is stored and used inside the Identity Data Database (IDDB).

It is both:
- a **design contract** for developers, and
- a **plain-language reference** for users.

---

## 1. Layers of memory

Codexify separates “what happened” from “who you are”.

### 1.1 Chat history (diary layer)

- We store your conversations as chat logs.
- This is like a diary or notebook:
  - scrollable,
  - searchable,
  - exportable.
- By default, chat logs are **not** treated as long-term identity traits. They are content, not labels.

### 1.2 Light identity modeling (default)

We maintain a minimal “imprint” of how you like to think and be spoken to. Examples:

- tone: gentle / direct / playful / clinical,
- structure: step-by-step vs overview,
- explanation style: analogies, examples, or straight answers,
- interaction habits: prefers summaries, asks for plans, etc.

We **do not** assign or persist labels about:
- your mental health,
- your political alignment,
- your trauma history,
- your religious affiliation,
- your sexual orientation or gender identity.

You can still talk about these freely in chat. They live in the diary layer, not as durable identity flags.

We call this layer **Imprint_Zero (Light)**.

### 1.3 Deep identity modeling (optional)

Deep identity is **opt-in**.

If enabled, Codexify may summarize:

- long-term goals and values,
- recurring life themes,
- detailed style/preferences,
- “identity markers” that help the system reason about you over time.

Deep identity lives in an **Identity Mirror** that you can:

- inspect,
- edit,
- delete,
- reset.

You can turn deep identity off at any time. Turning it off stops new traits from being added. You can also wipe everything it has learned so far.

---

## 2. Personas, Imprint_Zero, and masks

- **Imprint_Zero** is your underlying imprint: how you tend to think, speak, and reason.
- **Personas** are masks the assistant wears:
  - e.g. “Scholar”, “Coach”, “Gremlin”, “Project Manager”.

Personas never *own* your identity. They *borrow* it.

- All personas can read from the same underlying identity mirror **if you ask them to**.
- You can say:
  > “Act as Persona X but remember what I told Persona Y.”
- The system treats this as an explicit cross-persona retrieval from the same IDDB.

By default, each persona:
- talks in its own voice,
- primarily uses its own persona-tagged memories,
- but can reach across to other persona memories when you request it.

You remain the only stable identity in the system.

---

## 3. What is explicitly not inferred by default

Unless deep identity is enabled, Codexify does **not** create durable flags or traits for:

- clinical diagnoses,
- political labels,
- trauma summaries,
- religious identity,
- sexual orientation or gender identity.

These topics may appear in chat logs, but they are **not** promoted to long-lived identity features without explicit consent.

Future versions may support user-defined “sensitive topics” that are never used for modeling, even in deep mode.

---

## 4. Diary mode and exclusion from modeling

Some conversations are just for you.

- Any thread can be marked as **Diary**.
- Diary threads:
  - can require an extra unlock step,
  - can be fully excluded from identity modeling (light and deep), if you choose.

When excluded, content from that thread:
- is stored as plain chat history,
- is not used to update Imprint_Zero or Deep Identity,
- is still searchable by you if you choose.

This lets you explore difficult topics without fearing surprise resurfacing in other contexts.

---

## 5. Local privacy & access control

Codexify treats your identity data like a private journal or medical record.

Recommended protections (some optional, some default):

- App lock:
  - optional PIN / passphrase / biometric gate on opening Codexify Vault/Desktop,
  - optional auto-lock on idle or backgrounding.
- Visual indicator when the “private stack” (IDDB-aware mode) is active.
- Encrypted-at-rest identity tables where the platform allows it.
- Optional “paranoid mode”:
  - additional passphrase to decrypt identity records,
  - without it, identity rows are opaque even if the DB is copied.

If your device is compromised, your Codexify data can be as sensitive as any other secure app. Treat it with the same care as banking or medical data.

---

## 6. Reset and rollback

You can:

- reset Imprint_Zero and personas at any time,
- clear Deep Identity,
- export or delete your IDDB,
- pin your experience to a specific runtime version so that updates do not change your assistant’s personality without your consent.

The IDDB schema is designed to be:
- forward-compatible (new fields added without breaking old data),
- non-destructive (migrations are idempotent and logged),
- decoupled from specific model/runtimes.

Codexify exists to help you think, not to trap you in any particular profile.