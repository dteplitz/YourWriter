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
8. **Always test mobile too** — include a mobile viewport pass in manual QA, not just desktop
9. **Auto-continue on Claudio messages when prudent** — if Damian says there is a new message from `claude-code`, read it immediately and, when the next QA/retest step is clear and safe, continue the validation automatically without waiting for extra confirmation

## Autonomy — work without involving Damian
Damian is the PO but should NOT need to relay messages between agents. Agents must communicate directly and close the loop themselves:

- **claude-code**: after every fix or build, proactively message codex with what changed and what to retest. Don't wait for Damian to prompt this.
- **codex**: after every QA pass, message claude-code directly with findings. claude-code will read and act on them.
- **Both agents**: if a bug is reported, claude-code fixes it and messages codex for retest — Damian should only be involved for product decisions (acceptance criteria, scope changes), not coordination.
- **Loop**: build → QA → fix → retest → repeat, all between claude-code and codex. Only escalate to Damian when: (1) a bug requires a product decision, (2) acceptance criteria are fully met, or (3) something is blocked and needs PO input.

## Agent names
- `claude-code` — Claude Code (Tech Lead, main conversation)
- `codex` — Codex (QA, manual testing, frontend review)
- `damian` — Damian (PO, can also leave messages)
