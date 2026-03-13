# Inter-Agent Communication Protocol

## How it works
Agents communicate through `messages.md` in this directory. Each message is appended at the top (newest first).

## Message format
```
---
from: <agent-name>
to: <agent-name or "all">
date: <YYYY-MM-DD HH:MM>
status: new | acknowledged | resolved
---
<message body>
```

## Rules
1. **Always read before writing** — check for new messages addressed to you
2. **Acknowledge messages** — change status from `new` to `acknowledged` when you've read it
3. **Mark resolved** — when the issue/request is handled
4. **Be concise** — this is a coordination channel, not a chat
5. **Include context** — file paths, error messages, what you need
6. **Verify runtime facts before deep QA** — if a reported URL/port/runtime does not match what you actually observe in the browser, treat the message as a hint, not ground truth
7. **Escalate environment mismatches early** — if you see a different app, stale service worker output, or contradictory ports, stop the QA flow and ask for the canonical environment before reporting product bugs

## Agent names
- `claude-code` — Claude Code (Tech Lead, main conversation)
- `codex` — Codex (QA, manual testing, frontend review)
- `damian` — Damian (PO, can also leave messages)
