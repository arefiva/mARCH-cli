# PRD: Code Review Fixes for feature/prompt-system

## Overview

Fix four issues identified during code review of the `feature/prompt-system` branch. The issues range from a race condition in the bash task executor, a process reference leak, a fragile regex in context compaction, to massive test coverage loss across extension and networking subsystems.

## Goals

1. **Eliminate race condition** in `BashTaskExecutor._current_process` shared state.
2. **Fix process reference leak** on non-timeout exceptions.
3. **Harden summary extraction** against nested or malformed `<summary>` tags.
4. **Restore critical test coverage** for extension and networking subsystems that were deleted.

## Non-Goals

- Refactoring the extension or networking modules themselves.
- Adding new features to the bash executor or context compaction.
- Achieving 100% test coverage — only restoring tests for shipped code that lost coverage.

## User Stories

### US-001: Fix race condition and process leak in BashTaskExecutor

**Description:** As a developer running concurrent tasks, I want `BashTaskExecutor` to safely handle parallel `execute()` calls so that processes are never orphaned or incorrectly killed.

**Implementation Notes:**
- In `src/mARCH/tasks/bash_executor.py`, replace the shared `self._current_process` instance variable with a local variable scoped to the `execute()` method.
- Pass the local process reference into the timeout handler instead of reading from `self._current_process`. The `asyncio.wait_for` wraps `_run_command_streaming`, so the process reference must be accessible from the timeout handler. One approach: have `_run_command_streaming` return or set the process on a per-call context object, or use a local variable with a `finally` block.
- Remove `self._current_process` from `__init__` (line 27), `_run_command_streaming` (lines 191, 203), and the timeout handler (lines 105–108).
- In the timeout handler (`except asyncio.TimeoutError`), kill the process using the local reference. Wrap the kill in a try/except in case the process already exited.
- In the generic exception handler (`except Exception`, line 115), ensure any running process is also killed and awaited to prevent leaks. Add a `finally` block that cleans up the process reference.
- Update `tests/tasks/test_bash_executor.py` to add a concurrency test: launch two `execute()` calls with `asyncio.gather`, verify both complete without interfering with each other.
- Add a test for the non-timeout exception path: mock `_run_command_streaming` to raise a non-timeout exception and verify no stale process reference remains.

**Acceptance Criteria:**
- [ ] `self._current_process` instance variable is removed from `BashTaskExecutor.__init__`.
- [ ] `_run_command_streaming` no longer reads or writes `self._current_process`.
- [ ] The timeout handler kills the correct process via a local reference.
- [ ] A `finally` block ensures process cleanup on any exception path.
- [ ] Unit test verifies two concurrent `execute()` calls complete independently without cross-talk.
- [ ] Unit test verifies a non-timeout exception does not leak a process reference.
- [ ] ruff check passes with no errors.
- [ ] pytest passes with no failures.

---

### US-002: Harden summary extraction regex in ContextCompactor

**Description:** As a developer using context compaction, I want the summary extraction to handle nested or malformed `<summary>` tags so that compacted context is never silently corrupted.

**Implementation Notes:**
- In `src/mARCH/core/context_compaction.py`, method `_extract_summary` (line 149–157), replace the non-greedy regex `r"<summary>(.*?)</summary>"` with a greedy match `r"<summary>(.*)</summary>"` (with `re.DOTALL`). This ensures the match extends to the *last* `</summary>` tag, correctly handling nested occurrences.
- Consider whether a greedy match could over-capture when there are multiple top-level `<summary>` blocks. Since the summarization prompt asks for exactly one `<summary>` block, greedy is the correct choice — it captures everything between the first `<summary>` and the last `</summary>`.
- Add tests to `tests/test_phase6_agent.py` or create a new `tests/test_context_compaction.py` file for:
  - Normal extraction (no nesting).
  - Nested `<summary>` tags — verify full content is extracted.
  - Missing tags — verify fallback to raw response.
  - Empty `<summary></summary>` — verify empty string is returned.

**Acceptance Criteria:**
- [ ] `_extract_summary` uses greedy `(.*)` instead of non-greedy `(.*?)`.
- [ ] Unit test verifies extraction from `"<summary>hello</summary>"` returns `"hello"`.
- [ ] Unit test verifies extraction from `"<summary>Use <summary>x</summary> here</summary>"` returns `"Use <summary>x</summary> here"`.
- [ ] Unit test verifies missing tags fall back to raw response.
- [ ] Unit test verifies `"<summary></summary>"` returns empty string.
- [ ] ruff check passes with no errors.
- [ ] pytest passes with no failures.

---

### US-003: Restore extension subsystem test coverage

**Description:** As a maintainer, I want test coverage restored for the extension subsystem (`src/mARCH/extension/`) so that regressions in sandboxing, permissions, discovery, registry, manifest parsing, contracts, protocol, tool, and CLI command modules are caught.

**Implementation Notes:**
- The extension subsystem has 14 source modules in `src/mARCH/extension/` but only `test_extension_lifecycle.py` remains. The following test files were deleted and must be restored from the `main` branch: `test_extension_sandbox.py` (303 lines), `test_extension_discovery.py` (199 lines), `test_extension_registry.py` (243 lines), `test_extension_manifest.py` (217 lines), `test_extension_contracts.py` (157 lines), `test_extension_protocol.py` (193 lines), `test_extension_tool.py` (159 lines), `test_extension_cli_command.py` (120 lines), `test_extension_manager.py` (70 lines), `test_extension_integration.py` (150 lines).
- Use `git show main:tests/<filename>` to retrieve each deleted test file and recreate it.
- After restoration, run `pytest tests/test_extension_*.py` to verify all restored tests pass against the current source code.
- If any restored tests fail due to changes in the source modules on this branch, fix the tests to match the current API (do not change source code — only update test expectations or imports).
- The extension sandbox tests are security-critical: they validate permission isolation and must pass.

**Acceptance Criteria:**
- [ ] `tests/test_extension_sandbox.py` exists and passes (security-critical permission isolation tests).
- [ ] `tests/test_extension_discovery.py` exists and passes.
- [ ] `tests/test_extension_registry.py` exists and passes.
- [ ] `tests/test_extension_manifest.py` exists and passes.
- [ ] `tests/test_extension_contracts.py` exists and passes.
- [ ] `tests/test_extension_protocol.py` exists and passes.
- [ ] `tests/test_extension_tool.py` exists and passes.
- [ ] `tests/test_extension_cli_command.py` exists and passes.
- [ ] `tests/test_extension_manager.py` exists and passes.
- [ ] `tests/test_extension_integration.py` exists and passes.
- [ ] ruff check passes with no errors.
- [ ] pytest tests/test_extension_*.py passes with no failures.

---

### US-004: Restore networking subsystem test coverage

**Description:** As a maintainer, I want test coverage restored for the networking subsystem (`src/mARCH/networking/`) so that regressions in resilience (circuit breaker, retry, backoff), RPC, transport, and payload modules are caught.

**Implementation Notes:**
- The networking subsystem has 7 source modules in `src/mARCH/networking/` but only `test_networking_connection.py` and `test_networking_http_client.py` remain (both trimmed). The following test files were deleted: `test_networking_resilience.py` (339 lines), `test_networking_rpc.py` (331 lines), `test_networking_transport.py` (281 lines), `test_networking_payload.py` (207 lines).
- Use `git show main:tests/<filename>` to retrieve each deleted test file and recreate it.
- After restoration, run `pytest tests/test_networking_*.py` to verify all restored tests pass.
- If any restored tests fail due to source changes on this branch, fix the tests to match the current API.
- The resilience tests (circuit breaker, retry policies, exponential backoff) are particularly important for production reliability.

**Acceptance Criteria:**
- [ ] `tests/test_networking_resilience.py` exists and passes (circuit breaker, retry, backoff).
- [ ] `tests/test_networking_rpc.py` exists and passes.
- [ ] `tests/test_networking_transport.py` exists and passes.
- [ ] `tests/test_networking_payload.py` exists and passes.
- [ ] ruff check passes with no errors.
- [ ] pytest tests/test_networking_*.py passes with no failures.

---

### US-005: Restore core module test coverage (phase1/phase2 and analysis)

**Description:** As a maintainer, I want test coverage restored for core modules (stream buffer, shell executor, process manager, async executor, multi-file analysis) so that foundational infrastructure regressions are caught.

**Implementation Notes:**
- `tests/test_phase1_phase2.py` (523 lines) tested Phase 1 and Phase 2 core modules: `StreamBuffer`, `StreamManager`, `ShellExecutor`, `ProcessManager`, `TaskPool`, `CancelToken`. These are foundational infrastructure modules.
- `tests/test_analysis_multifile.py` (411 lines) tested multi-file analysis aggregation.
- Use `git show main:tests/<filename>` to retrieve each deleted test file and recreate it.
- After restoration, run `pytest tests/test_phase1_phase2.py tests/test_analysis_multifile.py` to verify all restored tests pass.
- If any restored tests fail due to source changes on this branch, fix the tests to match the current API.

**Acceptance Criteria:**
- [ ] `tests/test_phase1_phase2.py` exists and passes (stream buffer, shell executor, process manager, async executor).
- [ ] `tests/test_analysis_multifile.py` exists and passes (multi-file analysis aggregation).
- [ ] ruff check passes with no errors.
- [ ] pytest tests/test_phase1_phase2.py tests/test_analysis_multifile.py passes with no failures.

## Technical Considerations

- All test restorations (US-003, US-004, US-005) should use `git show main:tests/<file>` to recover the original test content, then adapt only what's needed for API compatibility.
- US-001 (race condition fix) is the most architecturally significant change — it modifies the executor's internal process management pattern.
- US-002 is a minimal but important regex fix with clear test cases.

## Open Questions

- None — all issues are well-defined with clear remediation paths.
