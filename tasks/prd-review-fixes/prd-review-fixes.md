# PRD: Code Review Fixes

## 1. Introduction/Overview

This PRD addresses four issues identified during a code review of the `feature/review-fixes` branch in the copilot-cli-python project. The issues range from a critical subprocess resource leak and a high-severity path validation bypass to medium-severity concerns around executor instance reuse and singleton staleness. Each user story targets one discrete issue to keep changes small and independently verifiable.

## 2. Goals

- Eliminate the subprocess resource leak in `BashTaskExecutor` so that failed stream reads always clean up the child process.
- Close the path-validation bypass in `FileTaskExecutor` that allows paths like `/tmpfoo/` to pass the temp-directory check.
- Reduce unnecessary object allocation in `get_default_registry()` by reusing stateless executor instances.
- Make `get_file_search()` safe against silent misconfiguration when called with different working directories.

## 3. User Stories

### US-001: Fix subprocess resource leak on stream failure

**Description:** As a developer running bash tasks, I want failed stream reads to always terminate the child process so that zombie processes never accumulate.

**Implementation Notes:**
- Modify `src/mARCH/tasks/bash_executor.py`, specifically the generic `except Exception` block at lines 115-122.
- Mirror the cleanup logic already present in the `except asyncio.TimeoutError` block (lines 103-108): call `self._current_process.kill()`, `await self._current_process.wait()`, and set `self._current_process = None`.
- Wrap the cleanup in a `try/except` to avoid masking the original exception if the process has already exited.
- Add a unit test in `tests/tasks/test_bash_executor.py` that patches `_read_stream` to raise, then asserts the process is killed and `_current_process` is reset to `None`.

**Acceptance Criteria:**
- [ ] Unit test verifies that when `_read_stream` raises a `RuntimeError`, the subprocess is killed and `_current_process` is `None` after `execute()` returns.
- [ ] Unit test verifies the returned `TaskResult` has `status="failed"` and an error message containing the original exception text.
- [ ] Unit test covers edge case: `_current_process` is already `None` when the exception fires (no crash).
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-002: Fix path validation bypass via prefix matching

**Description:** As a security-conscious operator, I want path validation to reject paths like `/tmpfoo/evil.txt` so that only genuine temp directories are allowed.

**Implementation Notes:**
- Modify `src/mARCH/tasks/file_executor.py`, specifically the `_validate_path` method around line 257.
- Replace `str(path).startswith("/tmp")` / `str(path).startswith("/var/tmp")` with `path.is_relative_to(Path("/tmp"))` and `path.is_relative_to(Path("/var/tmp"))`. `Path.is_relative_to` (Python 3.9+) checks proper directory containment, not string prefix.
- Optionally add `Path(tempfile.gettempdir()).resolve()` as a third allowed root to cover non-standard temp dirs.
- Add unit tests in `tests/tasks/test_file_executor.py`.

**Acceptance Criteria:**
- [ ] Unit test verifies `/tmp/safe/file.txt` passes validation.
- [ ] Unit test verifies `/var/tmp/safe/file.txt` passes validation.
- [ ] Unit test verifies `/tmpfoo/evil.txt` is rejected with `ValueError`.
- [ ] Unit test verifies `/var/tmpfoo/evil.txt` is rejected with `ValueError`.
- [ ] Unit test covers edge case: path that is exactly `/tmp` (no trailing component) passes validation.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-003: Reuse executor instances in default registry

**Description:** As a maintainer, I want `get_default_registry()` to share a single instance per executor type so that stateful executors (e.g., `BashTaskExecutor` with temp-file tracking) coordinate cleanup correctly and we avoid unnecessary object allocation.

**Implementation Notes:**
- Modify `src/mARCH/core/task_executor.py`, function `get_default_registry()` (lines 90-101).
- Create one `BashTaskExecutor()`, one `FileTaskExecutor()`, and one `AnalysisTaskExecutor()` instance, then register the same `FileTaskExecutor` instance for `FILE_READ`, `FILE_CREATE`, and `FILE_EDIT`.
- This is a straightforward refactor — no new files needed.
- Add a unit test that calls `get_default_registry()` and asserts that the executors registered for the three `FILE_*` task types are the same object (`is` identity check).

**Acceptance Criteria:**
- [ ] Unit test verifies the executor for `TaskType.FILE_READ`, `TaskType.FILE_CREATE`, and `TaskType.FILE_EDIT` are the same object instance.
- [ ] Unit test verifies `TaskType.BASH` and `TaskType.ANALYSIS` each have their own executor registered.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

---

### US-004: Prevent silent misconfiguration of file search singleton

**Description:** As a developer, I want `get_file_search()` to raise an error when called with a different `working_directory` than the cached instance so that I am not silently searching the wrong directory.

**Implementation Notes:**
- Modify `src/mARCH/cli/file_search.py`, function `get_file_search()` (lines 312-324).
- After checking `_search_instance is not None`, compare the requested `working_directory` against the instance's current directory. If they differ and `working_directory` is not `None`, raise a `ValueError` explaining the mismatch. This is the safest fix: it makes the contract explicit without silently swapping state.
- Also add a `reset_file_search()` function (for test teardown and explicit re-initialization) that sets `_search_instance = None`.
- Add unit tests in a new file `tests/cli/test_file_search.py`.

**Acceptance Criteria:**
- [ ] Unit test verifies first call with `/tmp/a` returns an instance configured for `/tmp/a`.
- [ ] Unit test verifies second call with `None` returns the same cached instance (no error).
- [ ] Unit test verifies second call with a *different* directory raises `ValueError`.
- [ ] Unit test verifies `reset_file_search()` clears the singleton, allowing a new directory on the next call.
- [ ] `ruff check` passes with no errors.
- [ ] `pytest` passes with no failures.

## 4. Non-Goals (Out of Scope)

- Refactoring the singleton pattern in `file_search.py` into a proper dependency-injection approach.
- Adding integration or end-to-end tests beyond unit-level verification.
- Changing the public API surface of any executor class.
- Addressing any issues not explicitly listed in the code review findings.

## 5. Technical Considerations

- `Path.is_relative_to()` requires Python 3.9+. The project already targets ≥ 3.10 (see `pyproject.toml`), so this is safe.
- The `reset_file_search()` helper is intentionally minimal — it only clears the module-level global for test isolation.

## 6. Open Questions

- None — all four issues have clear, self-contained fixes.
