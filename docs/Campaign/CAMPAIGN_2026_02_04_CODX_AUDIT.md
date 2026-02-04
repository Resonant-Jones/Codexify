Got it. I’ve read the audit and will treat the Findings Manifest as authoritative.

What do you want to do next? Pick a finding (or a bundle), and I’ll execute.

If helpful, here’s a focused default order based on risk/impact:
1) FINDING-2026-02-04-001 (.env committed with keys)
2) FINDING-2026-02-04-012 (documents/share unauthenticated)
3) FINDING-2026-02-04-002 (frontend auth relies on dev proxy)
4) FINDING-2026-02-04-003 (ChatGPT import unproxied)
5) FINDING-2026-02-04-005 (document-embed worker missing)

Tell me which ones to tackle first, and whether you want code changes only or also docs/tests.