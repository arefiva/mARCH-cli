# PRD: Code Review Fixes for feature/fix-plan-mode

## 1. Introduction/Overview

This PRD addresses five issues identified during code review of the `feature/fix-plan-mode` branch. The issues span two files — `src/mARCH/tasks/bash_executor.py` and `src/mARCH/tasks/file_executor.py` — and range from a critical shell injection vulnerability to a low-severity temp file leak. Fixing these issues hardens the task execution subsystem against security exploits, resource exhaustion, and subtle data-corruption bugs.

## 2. Goals

- Eliminate the shell injection attack surface in `BashTaskExecutor`
- Ensure subprocesses are always terminated on timeout (no zombie processes)
- Prevent subprocess deadlocks caused by sequential pipe reads
- Make file-edit operations safe against ambiguous multi-match replacements
- Clean up temporary overflow files to prevent disk exhaustion

## 3. User Stories

### US-001: Mitigate Shell Injection in Bash Executor

**Description:** As a platform operator, I want bash command execution to be protected against shell injection so that untrusted or partially-trusted command strings cannot escalate to arbitrary code execution.

**Implementation Notes:**
- Modify `src/mARCH/tasks/bash_executor.py` method `_run_command_streaming` (line 122)
- Replace `asyncio.create_subprocess_shell()` with `asyncio.create_subprocess_exec()` using `shlex.split(command)` to parse the command string into an argument list
- Add `import shlex` at the top of the file
- Handle edge cases: empty command after split, commands with quoted arguments, commands with environment variable references
- If full shell features (pipes, redirects) are genuinely required by callers, add a `shell=True` opt-in flag in `task.params` with a prominent docstring warning, and default to `shell=False`
- Add unit tests in a new file `tests/tasks/test_bash_executor.py`

**Acceptance Criteria:**
- [ ] Unit test verifies that a command string with shell metacharacters (e.g., `echo hello; rm -rf /`) is NOT executed through a shell when `shell` param is absent or false
- [ ] Unit test verifies that `shlex.split` correctly tokenises a quoted command like `echo "hello world"` into `["echo", "hello world"]`
- [ ] Unit test verifies that when `shell=True` is explicitly set in task params, `create_subprocess_shell` is used instead
- [ ] Unit test covers edge case: empty command after shlex.split raises a clear error
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### US-002: Kill Subprocess on Timeout and Clean Up Temp Files

**Description:** As a platform operator, I want timed-out subprocesses to be killed immediately and overflow temp files to be cleaned up so that the system does not leak zombie processes or disk space.

**Implementation Notes:**
- Modify `src/mARCH/tasks/bash_executor.py` method `execute` (lines 58-104)
- Store the `process` handle so it is accessible in the timeout handler — e.g., use an instance variable `self._current_process` set inside `_run_command_streaming` before `process.wait()`, or refactor to pass the process handle back
- In the `except asyncio.TimeoutError` block (line 89), call `process.kill()` then `await process.wait()` to reap the zombie
- For temp file cleanup: add a `cleanup()` or `__del__` method, or register an `atexit` handler that deletes files listed in a class-level set `_temp_files`
- Track created temp files by adding each path from `_create_temp_output_file()` to a set on the class instance
- Provide a public `cleanup_temp_files()` method that deletes all tracked files and clears the set
- Add unit tests in `tests/tasks/test_bash_executor.py`

**Acceptance Criteria:**
- [ ] Unit test verifies that after a timeout, `process.kill()` is called on the subprocess
- [ ] Unit test verifies that after a timeout, `process.wait()` is awaited (no zombie)
- [ ] Unit test verifies that `cleanup_temp_files()` deletes all tracked temp files from disk
- [ ] Unit test covers edge case: cleanup is idempotent — calling it twice does not raise
- [ ] Unit test covers edge case: cleanup handles already-deleted files gracefully (no FileNotFoundError)
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### US-003: Read stdout and stderr Concurrently to Prevent Deadlock

**Description:** As a platform operator, I want stdout and stderr to be read concurrently so that subprocesses producing large stderr output do not deadlock.

**Implementation Notes:**
- Modify `src/mARCH/tasks/bash_executor.py` method `_run_command_streaming` (lines 136-171)
- Extract the per-stream reading loop into a helper coroutine (e.g., `_read_stream(stream, buffer, size_tracker, label)`) that reads lines and handles overflow to disk
- Use `asyncio.gather()` or `asyncio.create_task()` to read stdout and stderr concurrently instead of sequentially
- Ensure the overflow file writing is still correct when both streams write to the same file — use a lock (`asyncio.Lock`) or separate overflow files per stream
- Keep the existing 100MB per-stream limit and overflow-to-disk behaviour intact
- Add unit tests in `tests/tasks/test_bash_executor.py`

**Acceptance Criteria:**
- [ ] Unit test verifies that a subprocess writing >64KB to stderr while stdout is still open does NOT deadlock (completes within 5 seconds)
- [ ] Unit test verifies that stdout and stderr content are both fully captured when both streams produce output simultaneously
- [ ] Unit test verifies that overflow-to-disk still works correctly when output exceeds MAX_OUTPUT_SIZE
- [ ] Unit test covers edge case: subprocess that produces no output on either stream returns empty strings
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

### US-004: Reject Ambiguous Multi-Match File Edits

**Description:** As a developer, I want file edit operations to fail explicitly when the search string matches multiple locations so that edits are never silently applied to the wrong occurrence.

**Implementation Notes:**
- Modify `src/mARCH/tasks/file_executor.py` method `_edit_file` (lines 299-310)
- After confirming `old_str in content` (line 302), add a count check: `if content.count(old_str) > 1: raise ValueError(...)`
- The error message should include the count and a truncated snippet of `old_str` for debuggability
- Add unit tests in a new file `tests/tasks/test_file_executor.py`

**Acceptance Criteria:**
- [ ] Unit test verifies that editing a file where `old_str` appears exactly once succeeds and produces the correct output
- [ ] Unit test verifies that editing a file where `old_str` appears 3 times raises `ValueError` with a message containing the count
- [ ] Unit test verifies that editing a file where `old_str` is absent raises `ValueError` (existing behaviour preserved)
- [ ] Unit test covers edge case: `old_str` that is a substring of a longer match is still counted correctly
- [ ] `ruff check` passes with no errors
- [ ] `pytest` passes with no failures

## 4. Non-Goals (Out of Scope)

- Refactoring the overall task executor architecture
- Adding new task types or executor capabilities
- Changing the `_validate_path` security model (confirmed correct during review)
- Performance optimisation of stream reading beyond fixing the deadlock
- Adding integration tests or end-to-end tests (unit tests only)

## 5. Technical Considerations

- **Backward compatibility:** Switching from `create_subprocess_shell` to `create_subprocess_exec` changes behaviour for commands that rely on shell features (pipes, globbing, redirects). The `shell=True` opt-in preserves this path for callers that need it.
- **Concurrency in stream reading:** If both stdout and stderr overflow to the same temp file, interleaved writes could corrupt data. Use separate temp files or an asyncio lock.
- **Process cleanup timing:** `process.kill()` sends SIGKILL which is not catchable. If graceful shutdown is needed, consider `process.terminate()` (SIGTERM) with a short grace period before `process.kill()`.

## 6. Open Questions

- Should `shell=True` opt-in be allowed at all, or should shell execution be completely removed? (Current recommendation: allow with explicit opt-in and documentation.)
- Should temp file cleanup happen automatically via `atexit`, or only when explicitly called? (Current recommendation: both — track files and provide a public cleanup method, plus register atexit as a safety net.)
