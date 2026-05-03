# PRD: Port GitHub Copilot CLI System Prompts to Python CLI

## Overview

Port the rich, structured system prompt architecture from the original JavaScript-based GitHub Copilot CLI (`Copilot-cli`) to the Python rewrite (`copilot-cli-python` / mARCH CLI). The current Python CLI has a minimal system prompt in `Agent._get_system_prompt()` that only includes basic identity and directory context. The JS CLI has ~15 distinct prompt sections covering agent identity, task guidelines, code change rules, memory injection, context compaction, custom instructions, and more. This feature brings parity.

## Goals

1. **Prompt parity**: Implement all high-value prompt sections from the JS CLI in the Python codebase.
2. **Modular architecture**: Create a `prompts.py` module with composable prompt sections rather than one monolithic string.
3. **Backward compatibility**: Existing tests and callers of `Agent._get_system_prompt()` and `get_conversation_context()` must continue working.
4. **Extensibility**: New prompt sections should be easy to add without modifying existing ones.

## Non-Goals

- Implementing actual tool execution (e.g., `report_intent` tool itself) — only the prompt text that instructs the AI about tools.
- Changing the AI model or API client layer.
- Full parity with JS CLI UI or slash commands.

## Current State

### What exists in Python (`src/mARCH/core/agent_state.py` lines 295-339)

- Basic identity: "You are {name}, an AI-powered coding assistant."
- CWD, language, branch context
- File listing (up to 20 files)
- One-line closing: "Be concise, helpful, and provide code examples when appropriate."

### What is missing (from JS CLI analysis)

| # | Prompt Section | JS Source | Priority |
|---|---------------|-----------|----------|
| 1 | Richer agent identity with role variants | 19-react-components.js:1327 | High |
| 2 | Task guidelines / tone (be concise, `<plan>` tags) | 19-react-components.js:1987 | High |
| 3 | Code change instructions | 19-react-components.js:1299 | High |
| 4 | Linting/building/testing rules | 19-react-components.js:2282 | High |
| 5 | Style rules | 19-react-components.js:2290 | Medium |
| 6 | Ecosystem tools instructions | 19-react-components.js:2273 | Medium |
| 7 | Tips and tricks | 19-react-components.js:2070 | Medium |
| 8 | Prohibited actions | 19-react-components.js:1341 | High |
| 9 | Environment context header | 20-react-rendering.js:13505 | Medium |
| 10 | Memory system injection | 20-react-rendering.js | Medium |
| 11 | Context compaction/summarization | 19-react-components.js:638 | Medium |
| 12 | Autopilot mode context injection | 20-react-rendering.js:12131 | Low |
| 13 | Custom instructions (.github/copilot-instructions.md) | 19-react-components.js:1364 | Medium |
| 14 | Quota insufficient message | 20-react-rendering.js:1572 | Low |
| 15 | Task not complete reminder | 20-react-rendering.js:1517 | Low |

## Architecture

### New module: `src/mARCH/core/prompts.py`

A module with a `PromptBuilder` class that assembles the system prompt from composable sections. Each section is a method that returns `str | None` (None = skip that section).

```
PromptBuilder
  ├── build_system_prompt(agent, context, **kwargs) -> str
  ├── _identity_section(agent_role) -> str
  ├── _task_guidelines_section() -> str
  ├── _code_change_section() -> str
  ├── _linting_testing_section() -> str
  ├── _style_section() -> str
  ├── _ecosystem_tools_section() -> str
  ├── _tips_section() -> str
  ├── _prohibited_actions_section() -> str
  ├── _environment_context_section(context) -> str
  ├── _memory_section(memories) -> str | None
  └── _custom_instructions_section(repo_root) -> str | None
```

### New module: `src/mARCH/core/context_compaction.py`

Handles conversation summarization when context window fills up:
- `ContextCompactor.should_compact(messages, max_tokens)` — detect when compaction needed
- `ContextCompactor.compact(messages, ai_client)` — generate summary and replace history
- `ContextCompactor.build_compacted_messages(summary, user_messages)` — format the compacted context

### New module: `src/mARCH/core/custom_instructions.py`

Reads custom instructions from `.github/copilot-instructions.md` (repo-level) and optionally org-level instructions. Handles priority/conflict resolution per JS CLI rules.

### Integration point

`Agent._get_system_prompt()` in `agent_state.py` will delegate to `PromptBuilder.build_system_prompt()`.

## User Stories

### US-001: Core System Prompt Refactor

Create `src/mARCH/core/prompts.py` with `PromptBuilder` class. Implement sections: identity (with task agent / coding agent variants), task guidelines, code change instructions, linting/testing rules, style rules, ecosystem tools, tips, and prohibited actions. Update `Agent._get_system_prompt()` to delegate to the new builder. Add `AgentRole` enum to distinguish task vs coding agent.

### US-002: Environment Context & Custom Instructions

Add environment context section (OS, git info, sandboxed header). Implement `src/mARCH/core/custom_instructions.py` to read `.github/copilot-instructions.md`. Integrate both into `PromptBuilder`.

### US-003: Memory System Prompt Injection

Add memory context section to `PromptBuilder` that, when memories are provided, injects the JS CLI's memory preamble explaining how to use/verify/refresh memories. Wire it into the prompt builder with a `memories` parameter.

### US-004: Context Compaction & Summarization

Create `src/mARCH/core/context_compaction.py`. Implement the summarization instruction prompt, the compacted history format, and the `should_compact` / `compact` methods. Integrate with `ConversationHistory`.

### US-005: Autopilot Mode Context Injection

Add mode transition messages to `PromptBuilder` for autopilot/interactive mode switches. Integrate with `ModeManager` to inject the correct message when a plan is approved.

### US-006: Quota & Task Completion Messages

Add quota-insufficient and task-not-complete prompt templates to `prompts.py`. Expose them as utility methods for the CLI layer to inject when needed.

## Technical Notes

- No new dependencies required — all prompt logic is pure string construction.
- The `prompts.py` module should have no side effects at import time.
- Memory section is conditional — only included when memories are non-empty.
- Custom instructions section is conditional — only included when the file exists.
- All strings should be defined as module-level constants or class constants for easy testing.
- Test file: `src/mARCH/tests/test_prompts.py`
