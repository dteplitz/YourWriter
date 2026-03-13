---
description: Read and write inter-agent messages (.comms/messages.md)
---

Read the file `.comms/messages.md` and `.comms/PROTOCOL.md`.

If the user provided arguments: write a new message at the TOP of `.comms/messages.md` (after the `# Agent Messages` header), following the format in PROTOCOL.md. Use "claude-code" as the `from` field. Ask the user who the message is `to` if not obvious from context.

If no arguments: read and display all messages with status `new` that are addressed to `claude-code` or `all`. After displaying, ask if any should be marked as `acknowledged`.

$ARGUMENTS
