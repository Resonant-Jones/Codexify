# Guardian CLI Guide

This document outlines the CLI commands available for interacting with the Guardian backend system.

Note: Prefer invoking the CLI via `guardian/guardian_main.py`. The hyphenated path `guardian/guardian-main.py` remains as a compatibility shim that forwards to the same app.

---

## Project Commands

### Create a Project
```
python guardian/guardian_main.py project:create "My Project Name"
```

### List All Projects
```
python guardian/guardian_main.py project:list
```

---

## Thread Commands

### Create a Thread
```
python guardian/guardian_main.py thread:create --project "My Project Name" --title "Thread Title"
```

### List Threads by Project
```
python guardian/guardian_main.py thread:list --project "My Project Name"
```

### Show Thread Lineage
```
python guardian/guardian_main.py thread:lineage --thread-id THREAD_ID
```

---

## Conversation Commands

### Create a Conversation
```
python guardian/guardian_main.py conversation:create --thread-id THREAD_ID --title "Conversation Title"
```

### List Conversations by Thread
```
python guardian/guardian_main.py conversation:list --thread-id THREAD_ID
```

### Show Conversation Lineage
```
python guardian/guardian_main.py conversation:lineage --conversation-id CONVERSATION_ID
```

---

## Codemap Commands

### Generate Codemap
```
python guardian/codemap/generate_codemap.py
```

### Query Codemap
```
python guardian/guardian_main.py codemap:query "What does create-conversation do?"
```

---

## MemoryOS Commands

### Show Memory Summary
```
python guardian/guardian_main.py memory:summary
```

---

> This CLI is designed to give developers complete visibility and control over Guardian’s memory and conversational scaffolding. More commands coming soon.
