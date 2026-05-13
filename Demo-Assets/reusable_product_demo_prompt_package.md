# Reusable Product Demo Prompt Package

Use this package when asking Codex, a browser agent, or a screen-capture-capable automation tool to record a product walkthrough video.

The package is designed for layered production:

1. **Capture pass**: record clean visual footage.
2. **Edit planning pass**: identify zoom/focus moments.
3. **Voiceover pass**: generate narration after the video exists.
4. **Final polish pass**: align narration, zooms, captions, and cuts.

---

# 0. Prompt Variables

Before running the prompt, replace the bracketed values below.

```text
[APP_NAME] = Codexify
[APP_URL] = http://localhost:5173
[DEMO_PROJECT_NAME] = Demo Product Walkthrough
[DEMO_IMPORT_FILE] = conversations.json
[DEMO_PERSONA_NAME] = Jordan Lee
[DEMO_PERSONA_DESCRIPTION] = A synthetic demo user created only for product walkthroughs.
[PRIMARY_DEMO_GOAL] = Show the main interface, menus, chat configuration, provider switching, project creation, conversation import, and conversation organization flows.
[VOICEOVER_STATUS] = Voiceover will be generated later in a separate pass.
[CAPTURE_STYLE] = polished product walkthrough, not frantic QA clicking
[OUTPUT_AUDIENCE] = beta users, landing page visitors, internal QA reviewers, and potential early customers
```

---

# 1. Main Task Prompt

```text
You are GPT-5.5 Codex operating as a browser-based product demo and QA capture agent with access to a Screen Capture Tool.

Your task is to record a polished product video demo of [APP_NAME] running at:

[APP_URL]

This is a video capture task, not a code modification task.

Do not edit application code unless explicitly instructed. Use the application like a real user. Explore the interface deliberately, show the major workflows, and capture clear source footage that can later receive voiceover, zoom edits, captions, and final polish.

The demo should feel like a guided product walkthrough, not a random click test.

Primary demo goal:

[PRIMARY_DEMO_GOAL]

Audience:

[OUTPUT_AUDIENCE]
```

---

# 2. Operating Rules

```text
Follow these rules throughout the recording:

1. Use the Screen Capture Tool to record the browser window or full application viewport.
2. Keep cursor movement smooth and intentional.
3. Pause briefly after important clicks so viewers can see what changed.
4. Avoid rapid clicking.
5. Avoid exposing unnecessary browser chrome.
6. Keep the application centered and readable.
7. Do not record live narration unless explicitly instructed.
8. Do not expose API keys, provider secrets, private user data, passwords, or personal browser/account information.
9. If secrets appear on screen, stop and redo that segment with the secret hidden or blurred.
10. If a workflow fails, capture the failure clearly and continue. Do not pretend the workflow succeeded.
11. If a destructive action appears, show the menu or modal only if there is a safe cancel path.
12. If the UI path is unclear, explore cautiously and document what you found.
```

---

# 3. Recording Requirements

```text
Record the demo in a clean, readable format.

Recommended recording settings:

- Capture at 1080p or higher if available.
- Enable visible cursor capture if supported.
- Use a stable zoom level by default.
- Use zoom/focus emphasis only for important controls or dense UI areas.
- Leave short pauses for future narration.
- End each workflow on a visible result state when possible.

Do not record final voiceover during this pass.

[VOICEOVER_STATUS]
```

---

# 4. Demo Flow

Follow this sequence unless the application requires a different order.

## 4.1 Open the Application

```text
Navigate to:

[APP_URL]

Wait for the application to fully load.

Capture the initial landing, dashboard, or workspace state.

Briefly orient the viewer to the major interface regions:

- Sidebar or primary navigation.
- Main content area.
- Chat area.
- Settings or provider controls.
- Project, document, or conversation areas.
- Any visible status indicators.

Pause long enough for the viewer to understand the layout.
```

## 4.2 Explore Navigation and Menus

```text
Click through the primary navigation items.

For each visible section:

1. Open the section.
2. Pause for 2 to 4 seconds.
3. Hover over important controls.
4. Open obvious dropdowns, popovers, drawers, tabs, or menus.
5. Show what each menu contains.
6. Close menus cleanly before moving on.

Prioritize showing:

- Sidebar items.
- Settings menus.
- Profile or account menu, if safe.
- Model menus.
- Provider menus.
- Project menus.
- Conversation menus.
- Import/export controls.
- Document controls.
- Command palette, context menu, kebab menu, plus button, or floating action button.

Do not click destructive actions unless there is a visible safe cancel path.

If a modal opens, show it, then cancel or close it unless that workflow requires completion.
```

## 4.3 Demonstrate Model, Mode, and Source Selection

```text
In the chat interface:

1. Open the model selector.
2. Show available models.
3. Select an appropriate model.
4. Open the mode selector.
5. Show available modes.
6. Select one mode.
7. Open the source selector.
8. Show available source or context options.
9. Select one source.

Use zoom/focus emphasis for each selector if the Screen Capture Tool supports it.

Pause after each selection so the selected state is visible.
```

## 4.4 Send a Message

```text
In the chat input, send a simple product-safe message such as:

"Hello [APP_NAME]. Show me how you respond using the selected model, mode, and source."

or:

"Give me a concise summary of what this workspace contains."

After sending:

1. Capture the message appearing in the conversation.
2. Wait for the response to begin.
3. Capture streaming, loading, success, or error states.
4. If reasonable, wait for the response to complete.
5. If the response fails, capture the error state clearly and continue.
```

## 4.5 Change Inference Provider On Screen

```text
Locate the inference provider control or settings area.

Demonstrate changing providers visibly on screen.

Suggested sequence:

1. Open the provider selector or provider settings.
2. Show the currently selected provider.
3. Change to a different available provider.
4. Pause so the new provider state is visible.
5. Return to the chat interface.

If provider credentials are missing or a provider is unavailable:

- Show the UI state.
- Do not enter secrets.
- Do not expose API keys.
- Continue with any available provider or safely show the provider configuration screen.
```

## 4.6 Start a Chat With a Different Provider

```text
After changing providers:

1. Start a new chat or clear context using the intended UI path.
2. Confirm the new provider remains selected.
3. Select a compatible model if required.
4. Send a second simple message, such as:

"Respond in one sentence using the currently selected provider."

5. Capture the response or any provider-specific loading/error state.

The purpose is to show that provider switching affects chat initiation and message sending.
```

## 4.7 Create a Project

```text
Navigate to the Projects area.

Create a new project using this name:

[DEMO_PROJECT_NAME]

Recommended sequence:

1. Open the project creation control.
2. Show the creation modal or form.
3. Fill in the project name.
4. Add a short description if the UI supports it:

"Temporary project created for product demo recording."

5. Submit or create the project.
6. Show the newly created project in the project list or project view.

Use zoom/focus emphasis on the project creation form and final created state.
```

## 4.8 Import Demo Conversation Archive

```text
Navigate to the conversation import area or wherever conversation import is supported.

Use the provided synthetic demo file:

[DEMO_IMPORT_FILE]

This file represents a fictional user persona named [DEMO_PERSONA_NAME].

[DEMO_PERSONA_DESCRIPTION]

Do not describe or treat this file as real personal user history. Use it only to demonstrate the import workflow, conversation browsing, project organization, and conversation movement features.

Recommended sequence:

1. Open the import menu or import page.
2. Show accepted file type or import instructions if visible.
3. Select [DEMO_IMPORT_FILE].
4. Start the import.
5. Capture import progress, success state, summary, or failure state.
6. If imported conversations appear, show the resulting conversation list at a high level.
7. Avoid zooming deeply into individual conversation content unless needed to demonstrate the UI.

If no import file is available:

- Demonstrate the import UI.
- Capture the missing-file or unavailable-file state.
- Document that the import file was not available.
```

## 4.9 Move a Conversation to a Different Project

```text
After import, or using an existing conversation:

1. Locate one conversation.
2. Open its menu, context actions, or project assignment controls.
3. Choose the option to move, assign, or relocate it to a project.
4. Select [DEMO_PROJECT_NAME] or another safe target project.
5. Confirm the move.
6. Navigate to the target project.
7. Show that the conversation now appears in the target project.

If the application uses drag-and-drop:

- Demonstrate the drag slowly and clearly.
- Pause after dropping.
- Show the updated project or conversation state.

If moving is not available:

- Record the closest visible UI path.
- Document that the move workflow was not found.
```

## 4.10 Final Interface Sweep

```text
End with a polished final sweep.

Show:

- Dashboard or main workspace.
- Created demo project.
- Conversation list or imported conversation area.
- Chat/provider area.
- Any visually strong product state.

Do not end on:

- File picker.
- Error modal.
- Half-open menu.
- Secret-bearing settings screen.

End on a clean, stable screen suitable for a landing page, beta onboarding video, or voiceover outro.
```

---

# 5. Zoom and Focus Edit Requirements

```text
Include zoom and focus edits during recording or in post-production if the tool supports them.

Use zoom/focus emphasis for:

1. Model selector dropdown.
2. Mode selector.
3. Source selector.
4. Inference provider switcher.
5. Chat input and sent message.
6. Project creation modal or form.
7. Conversation import flow.
8. Selected import file name.
9. Import progress or completion state.
10. Conversation movement controls.
11. Important menus with multiple options.

Guidelines:

- Use zooms sparingly and intentionally.
- Zoom only long enough to make the UI readable.
- Return to the full interface after each highlighted action.
- Avoid excessive cinematic movement.
- Prioritize clarity over style.
- If focus blur is available, use it gently to direct attention without hiding functionality.
- If zoom/focus edits are not supported directly by the capture tool, record clean footage and produce a timestamped edit plan for later post-production.
```

---

# 6. Voiceover Planning Requirements

```text
Do not generate or record final voiceover during the capture pass.

After the video is captured, produce a timestamped narration outline for a future voiceover pass.

The narration outline should include:

- Timestamp range.
- What is happening on screen.
- Suggested voiceover text.
- Notes for emphasis.
- Any zoom/focus moments that should align with narration.

The future voiceover should explain:

1. What [APP_NAME] is.
2. How the interface is organized.
3. How users select models, modes, and sources.
4. How provider routing works from the user perspective.
5. How projects organize work.
6. How imported conversations become usable context.
7. How conversations can be moved into projects.
8. Why the interface supports both casual and advanced workflows.

Voiceover tone:

- Clear.
- Confident.
- Product-focused.
- Warm.
- Trust-building.
- Not mystical.
- No overclaiming.
- Avoid jargon unless the interface itself uses it.

For the import section, use this trust-building line or a close variant:

"For this walkthrough, we are using a synthetic conversation archive for [DEMO_PERSONA_NAME], a fictional demo user, so we can show the import workflow without exposing private chat history."
```

---

# 7. Safety and Privacy Requirements

```text
Do not expose:

- API keys.
- Provider secrets.
- Private user data.
- Personal conversations.
- Browser passwords.
- Account details.
- Local filesystem paths beyond what is necessary for file selection.
- Private imported conversation content beyond what is necessary to show the workflow.

If secrets appear on screen:

1. Stop that segment.
2. Redo it with secrets hidden, blurred, or avoided.
3. Document the correction.

If private conversation content appears:

1. Avoid zooming into it.
2. Use list-level views where possible.
3. Continue with the synthetic demo archive when available.
```

---

# 8. Output Requirements

```text
At the end of the task, provide:

1. The recorded video file.
2. A short summary of what was successfully captured.
3. A list of workflows completed.
4. A list of workflows that could not be completed.
5. Any bugs, confusing states, broken buttons, missing labels, or UX friction observed.
6. A timestamped edit plan for zoom/focus moments.
7. A timestamped voiceover outline for the next pass.
8. Any recommended retakes.
```

---

# 9. Quality Bar

```text
The final captured footage should be suitable as source material for:

- Product demo.
- Landing page walkthrough.
- Narrated product explainer.
- Internal QA review.
- Investor or beta-user onboarding.

Prioritize:

- Clear visual sequencing.
- Complete workflow coverage.
- Smooth pacing.
- Accurate interface representation.
- Honest failure capture.
- No exposed secrets.
- No fake claims.
- Strong final screen.

Record the app honestly, clearly, and calmly.
```

---

# 10. Optional Director Mode Addendum

Use this addendum when the footage should feel more like a launch walkthrough and less like internal QA footage.

```text
Director Mode Addendum:

Capture the demo as if this footage will become the foundation for a polished launch video.

Use the rhythm of a guided product walkthrough:

- Establish the full interface before showing details.
- Zoom only when the viewer needs to understand a control.
- Let important menus breathe on screen.
- Avoid moving the cursor while the viewer is reading.
- Use clean transitions between workflows.
- Prefer full-screen context before close-up detail.
- End each workflow with a visible successful result.

Think in chapters:

1. Workspace overview.
2. Chat configuration.
3. Provider routing.
4. Project creation.
5. Conversation import.
6. Conversation organization.
7. Final product state.

For every chapter, capture:

- The entry point.
- The action.
- The result.
- A clean pause for narration.

Do not explain everything at once. The voiceover will be layered later, so the footage should provide clear visual anchors the script can attach to.
```

---

# 11. Optional Synthetic Demo Persona Module

Use this when you need demo-safe imported data instead of private user data.

```text
Synthetic Demo Persona Module:

For this product demo, use a synthetic demo archive instead of real personal data.

Demo persona:

Name: [DEMO_PERSONA_NAME]
Description: [DEMO_PERSONA_DESCRIPTION]
Import file: [DEMO_IMPORT_FILE]

This persona exists only for the demo. Do not treat the archive as real private history. Do not imply that the conversations belong to a real person.

Use the synthetic archive to demonstrate:

1. Importing conversation history.
2. Browsing imported conversations.
3. Assigning or moving conversations into projects.
4. Showing how imported context becomes organized inside [APP_NAME].

For narration, briefly explain:

"For this walkthrough, we are using a synthetic conversation archive for [DEMO_PERSONA_NAME], a fictional demo user, so we can show the import workflow without exposing private chat history."
```

---

# 12. Optional Voiceover Generation Prompt

Use this after the footage has been recorded.

```text
You are creating a voiceover script for a product demo video of [APP_NAME].

Use the recorded video and timestamped capture notes as source material.

Write a clear, product-focused narration script that explains what is happening on screen without overclaiming.

Requirements:

1. Keep the tone confident, warm, and practical.
2. Explain benefits in user-facing language.
3. Avoid jargon unless the UI itself uses that term.
4. Do not mention implementation details unless they are visible or necessary.
5. Keep narration aligned with the actual footage.
6. Include a privacy-safe explanation when the synthetic demo archive appears.
7. Make the script easy to record in one pass.

Output format:

- Timestamp range.
- On-screen action.
- Voiceover line.
- Optional edit/caption note.

Include this line or a close variant during the import section:

"For this walkthrough, we are using a synthetic conversation archive for [DEMO_PERSONA_NAME], a fictional demo user, so we can show the import workflow without exposing private chat history."
```

---

# 13. Optional Post-Production Edit Prompt

Use this after the capture and voiceover script exist.

```text
You are editing a product demo video for [APP_NAME].

Use the recorded footage, timestamped edit plan, and voiceover script.

Create a final edit plan that includes:

1. Opening title or intro moment.
2. Segment boundaries.
3. Zoom/focus moments.
4. Cursor pauses.
5. Captions or callouts.
6. Sections to trim.
7. Sections to retake.
8. Voiceover alignment notes.
9. Final outro screen.

Editing priorities:

- Clarity over spectacle.
- Smooth pacing.
- Readable interface details.
- No exposed secrets.
- No misleading claims.
- Keep the viewer oriented.

Output a timestamped shot list and final render checklist.
```

---

# 14. Quick-Start Version

Use this shorter version when you already know the app and just need Codex to capture a demo quickly.

```text
Record a polished product demo of [APP_NAME] at [APP_URL] using the Screen Capture Tool.

This is a capture task, not a code editing task.

Show the main interface, navigation, menus, model/mode/source selection, sending a message, provider switching, starting a chat with another provider, creating a project, importing [DEMO_IMPORT_FILE], and moving one conversation into [DEMO_PROJECT_NAME].

Use [DEMO_IMPORT_FILE] as a synthetic demo archive for [DEMO_PERSONA_NAME]. Do not treat it as real private history.

Record clean visual footage only. Do not record final voiceover yet.

Use zoom/focus emphasis for important controls, especially selectors, provider switcher, project creation, import flow, and conversation movement.

Avoid exposing secrets or private data. If a workflow fails, capture the failure clearly and document it.

At the end, provide the video file, workflow summary, bugs/UX friction, timestamped zoom/focus edit plan, and timestamped voiceover outline.
```
