# Preflight Report (20250817-182648)

## Git
- head: dba31a6
- branch: chore/batch-run-001
```
## chore/batch-run-001
 M Makefile
?? artifacts/preflight/20250817-182648/
```

## Tools
- node: v22.17.0
- npm: 10.9.2
- yarn: not found
- pnpm: 10.13.1
- git: git version 2.39.5 (Apple Git-154)
- docker: Docker version 28.3.0, build 38b7060
- os: Darwin Christophers-MacBook-Air.local 24.6.0 Darwin Kernel Version 24.6.0: Mon Jul 14 11:30:40 PDT 2025; root:xnu-11417.140.69~1/RELEASE_ARM64_T8132 arm64

## Env
- env file: exists

### .env snapshot (redacted)
    # Google Gemini API Key for language model access
    GEMINI_API_KEY=AI****
    GENAI_API_KEY=FA****
    # Google API Key for YouTube Data API fallback (server quota)
    GOOGLE_API_KEY=AI****
    GOOGLE_CLIENT_ID=57****
    # Database file location (optional; default is guardian.db)
    GUARDIAN_DB_PATH=gu****
    POSTGRES_URL=po****
    # Notion API Key (if using Notion integrations)
    NOTION_API_KEY=nt****

    NOTION_DATABASE_ID=20****
    # .env.template
    # Environment configuration template for Guardian backend

    OPENAI_API_KEY=du****
    ANTHROPIC_API_KEY=sk****
    GROQ_API_KEY=gs****
    DEBUG=tr****
    LOG_LEVEL=IN****
    ENV=de****
    # Optional additions if your system evolves
    DATABASE_URL=yo****
    ADMIN_EMAIL=ad****
    CACHE_ENABLED=fa****
    PORT=80****
    # Default LLM Models
    GROQ_MODEL=me****
    OPENAI_MODEL=4.****
    GEMINI_MODEL=ge****
    ANTHROPIC_MODEL=cl****

    # Select active AI backend provider
    AI_BACKEND=gr****

## Ports
- 3000: free

- 5173: BUSY
COMMAND   PID           USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
node    45327 resonant_jones   12u  IPv6 0xc7edfeada9983493      0t0  TCP [::1]:5173 (LISTEN)

- 8000: free

- 5432: BUSY
COMMAND   PID           USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
postgres 1337 resonant_jones    7u  IPv6 0x2c9fdf367060b372      0t0  TCP [::1]:5432 (LISTEN)
postgres 1337 resonant_jones    8u  IPv4 0x44faf0f1b3feca64      0t0  TCP 127.0.0.1:5432 (LISTEN)



## Prompt & Manifest
- docs/prompts/infra-codex-pack.md: ok
- docs/prompts/run-manifest.yml: ok

## Preserved files
- src/TagSelector.tsx: present
- src/ThreadPromptBox.tsx: present
- src/PersonaEngine.ts: present
