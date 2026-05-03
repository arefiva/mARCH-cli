# Feature Context — mARCH CLI

> Port rich system prompt architecture from JS Copilot CLI to Python CLI — identity, guidelines, code change rules, memory injection, context compaction, custom instructions, and mode-specific messages.

> **Auto-generated sections below — custom sections are preserved.**
> Add custom notes in the 'Custom Context' section at the bottom.

## Story Groups

### System
- **PS-001**: Core system prompt builder with all static sections (priority 1)
- **PS-003**: Memory system prompt injection (priority 3)

### Context
- **PS-002**: Environment context and custom instructions (priority 2)
- **PS-004**: Context compaction and summarization (priority 4)
- **PS-005**: Autopilot mode context injection and utility messages (priority 5)

## Schema Extensions

- `compact_if_needed`
- `get_conversation_context`

## Cross-Module Touch Points

_No cross-module touch points detected._

## Known Constraints

_No constraints defined in aes.json. Add a `constraints` list if needed._
