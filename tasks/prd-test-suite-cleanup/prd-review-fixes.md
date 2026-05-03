# PRD: Test Suite Cleanup — Code Review Fixes

## 1. Introduction/Overview

The `feature/test-suite-cleanup` branch removed 17 test files and modified 10 others to reduce the test suite from ~813 to ~220 tests. A code review identified one bug (missing `WAITING_INPUT` assertion) and critical test coverage gaps across 29 production modules (~8,200 LOC) that now have zero test coverage. This PRD defines the work to restore minimal test coverage for all affected modules and fix the assertion bug.

## 2. Goals

- Fix the `AgentState.WAITING_INPUT` assertion bug in `test_phase6_agent.py`
- Restore at least one happy-path test per uncovered production module
- Cover critical edge cases for I/O and process-management modules (networking, core infra)
- Ensure all new tests pass and no existing tests break
- Keep the test count reasonable (target: add ~60–80 focused tests, not restore all ~590 deleted)

## 3. User Stories

### US-001: Fix Missing WAITING_INPUT Assertion

**Description:** As a developer, I want the agent state test to verify all 6 enum values so that state regressions are caught.

**Implementation Notes:**
- Edit `tests/test_phase6_agent.py`, method `test_agent_states_exist` (around line 42)
- Add back the assertion: `assert AgentState.WAITING_INPUT in AgentState`
- Verify the enum in `src/mARCH/core/agent_state.py` still defines `WAITING_INPUT = "waiting_input"` (line 22)

**Acceptance Criteria:**
- [ ] `test_agent_states_exist` asserts all 6 `AgentState` values including `WAITING_INPUT`
- [ ] `pytest tests/test_phase6_agent.py -v` passes with no failures
- [ ] `ruff check` passes with no errors

---

### US-002: Restore Extension Module Tests — Batch 1 (contracts, discovery, manifest, cli_command, tool)

**Description:** As a developer, I want minimal test coverage for the first batch of extension modules so that regressions in contracts, discovery, manifest parsing, CLI commands, and tool handling are caught.

**Implementation Notes:**
- Create `tests/test_extension_core.py` covering 5 modules: `contracts.py`, `discovery.py`, `manifest.py`, `cli_command.py`, `tool.py`
- For `contracts.py` (~87 LOC): test `ExtensionCapability`, `ExtensionPermission`, `ExtensionManifest`, and `ExtensionStatus` model creation and validation
- For `discovery.py` (~191 LOC): test `ExtensionDiscovery` scanning a tmp directory with/without valid manifests
- For `manifest.py` (~141 LOC): test `ManifestLoader` loading valid TOML/JSON and rejecting invalid manifests
- For `cli_command.py` (~194 LOC): test `CliCommand` creation with name/callback, `CliCommandRegistry` registration and lookup
- For `tool.py` (~206 LOC): test `ExtensionTool` creation and `ToolRegistry` add/get/list operations
- Follow the existing pattern in `test_extension_lifecycle.py` for imports and test class structure
- Use `tmp_path` fixture for filesystem operations; use simple mocks where external dependencies are needed

**Acceptance Criteria:**
- [ ] Unit test verifies `ExtensionManifest` accepts valid fields and rejects missing required fields
- [ ] Unit test verifies `ExtensionDiscovery` returns empty list for an empty directory
- [ ] Unit test verifies `ManifestLoader` raises an error for invalid manifest content
- [ ] Unit test verifies `CliCommand` stores name and callback correctly
- [ ] Unit test verifies `ToolRegistry.get` returns `None` for unknown tool names
- [ ] Edge case: `ExtensionCapability` with empty methods list is valid
- [ ] `pytest tests/test_extension_core.py -v` passes with no failures
- [ ] `ruff check` passes with no errors

---

### US-003: Restore Extension Module Tests — Batch 2 (manager, protocol, registry, sandbox)

**Description:** As a developer, I want minimal test coverage for the remaining extension modules so that regressions in extension management, protocol handling, registry, and sandboxing are caught.

**Implementation Notes:**
- Create `tests/test_extension_infra.py` covering 4 modules: `manager.py`, `protocol.py`, `registry.py`, `sandbox.py`
- For `manager.py` (~208 LOC): test `ExtensionManager` initialization, loading an extension, and listing loaded extensions
- For `protocol.py` (~240 LOC): test protocol message creation, serialization, and deserialization
- For `registry.py` (~269 LOC): test `ExtensionRegistry` register/unregister/lookup operations and duplicate-name handling
- For `sandbox.py` (~220 LOC): test `Sandbox` creation with different `SandboxLevel` values and permission checks
- Follow `test_extension_lifecycle.py` patterns; use mocks for I/O-heavy operations
- Use `tmp_path` for any filesystem needs

**Acceptance Criteria:**
- [ ] Unit test verifies `ExtensionManager` starts with empty extension list
- [ ] Unit test verifies protocol message round-trips through serialize/deserialize
- [ ] Unit test verifies `ExtensionRegistry` raises or returns error on duplicate registration
- [ ] Unit test verifies `Sandbox` restricts operations based on `SandboxLevel`
- [ ] Edge case: unregistering a non-existent extension returns gracefully
- [ ] `pytest tests/test_extension_infra.py -v` passes with no failures
- [ ] `ruff check` passes with no errors

---

### US-004: Restore Networking Module Tests (http_client, payload, resilience, rpc, transport)

**Description:** As a developer, I want minimal test coverage for networking modules so that regressions in HTTP client, payload handling, resilience, RPC, and transport are caught.

**Implementation Notes:**
- Create `tests/test_networking_core.py` covering 5 modules: `http_client.py`, `payload.py`, `resilience.py`, `rpc.py`, `transport.py`
- For `http_client.py` (~448 LOC): test `HttpClient` initialization and configuration; mock `httpx` for request/response testing
- For `payload.py` (~334 LOC): test `PayloadCodec` encode/decode round-trip, `PayloadValidator` accept/reject, `PayloadFormat` enum
- For `resilience.py` (~383 LOC): test `RetryPolicy` configuration, `ResilientClient` retry behavior with mocked failures
- For `rpc.py` (~493 LOC): test RPC message creation, method dispatch, and error handling
- For `transport.py` (~413 LOC): test transport layer initialization and connection lifecycle
- Follow `test_networking_connection.py` patterns; heavily mock external I/O (httpx, asyncio)
- Use `pytest-asyncio` for async tests if needed

**Acceptance Criteria:**
- [ ] Unit test verifies `HttpClient` initializes with correct default configuration
- [ ] Unit test verifies `PayloadCodec` round-trips a dict through encode then decode
- [ ] Unit test verifies `RetryPolicy` respects max retries configuration
- [ ] Unit test verifies RPC error response is returned for unknown method calls
- [ ] Edge case: `PayloadValidator` rejects payload exceeding size limit
- [ ] Edge case: `ResilientClient` exhausts retries and raises after max attempts
- [ ] `pytest tests/test_networking_core.py -v` passes with no failures
- [ ] `ruff check` passes with no errors

---

### US-005: Restore Core Infrastructure Tests (stream_buffer, shell_executor, process_manager, async_executor, payload_handler)

**Description:** As a developer, I want minimal test coverage for core infrastructure modules so that regressions in stream management, shell execution, process management, async task handling, and payload handling are caught.

**Implementation Notes:**
- Create `tests/test_core_infra.py` covering 5 modules: `stream_buffer.py`, `shell_executor.py`, `process_manager.py`, `async_executor.py`, `payload_handler.py`
- For `stream_buffer.py` (~333 LOC): test `StreamBuffer` write/read, `StreamMode` enum, `StreamManager` add/get streams
- For `shell_executor.py` (~362 LOC): test `ShellExecutor` running a simple command (e.g., `echo hello`), `CommandResult` fields
- For `process_manager.py` (~321 LOC): test `ProcessManager` tracking processes, `ProcessStatus` states
- For `async_executor.py` (~355 LOC): test `TaskPool` submit and await, `CancelToken` cancellation, `TaskPriority` enum
- For `payload_handler.py` (~345 LOC): test `PayloadCodec` encode/decode, `PayloadValidator` validation, `PayloadFormat` enum
- Follow patterns in `test_phase1_foundation.py`; mock subprocess/process operations
- Use `asyncio` test patterns for async methods

**Acceptance Criteria:**
- [ ] Unit test verifies `StreamBuffer` write then read returns the written data
- [ ] Unit test verifies `ShellExecutor` returns a `CommandResult` with stdout for a simple echo command
- [ ] Unit test verifies `ProcessManager` tracks a newly started process
- [ ] Unit test verifies `TaskPool` executes a submitted coroutine and returns its result
- [ ] Unit test verifies `CancelToken` transitions to cancelled state
- [ ] Edge case: `StreamBuffer` read on empty buffer returns empty or blocks appropriately
- [ ] Edge case: `ShellExecutor` returns non-zero exit code for a failing command
- [ ] `pytest tests/test_core_infra.py -v` passes with no failures
- [ ] `ruff check` passes with no errors

---

### US-006: Restore Parsing Module Tests (command_parser, text_parser, encoding_utils, string_transform, data_validation)

**Description:** As a developer, I want minimal test coverage for parsing modules so that regressions in command parsing, text parsing, encoding, string transformation, and data validation are caught.

**Implementation Notes:**
- Create `tests/test_parsing_core.py` covering 5 modules: `command_parser.py`, `text_parser.py`, `encoding_utils.py`, `string_transform.py`, `data_validation.py`
- For `command_parser.py` (~323 LOC): test `CommandParser.parse` with flags, positionals, and subcommands; verify `ParsedCommand` fields
- For `text_parser.py` (~376 LOC): test `TextParser` parsing structured text, `TextFormat` enum values
- For `encoding_utils.py` (~351 LOC): test `Encoder`/`Decoder` round-trip for supported `EncodingFormat` values (e.g., base64, utf-8)
- For `string_transform.py` (~382 LOC): test `StringTransform` case conversions, `CaseStyle` enum, `TextFormatter` format operations
- For `data_validation.py` (~398 LOC): test `DataValidator` accept/reject, `DataNormalizer` normalizing input, `SanitizationRules`
- Follow patterns in `test_phase2_cli.py` for CLI/parsing test structure
- Pure functions — no mocking needed for most tests

**Acceptance Criteria:**
- [ ] Unit test verifies `CommandParser.parse("--verbose run tests")` produces correct flags and positionals
- [ ] Unit test verifies `Encoder`/`Decoder` round-trip preserves original data
- [ ] Unit test verifies `StringTransform` converts "hello world" to "HELLO WORLD" in upper case style
- [ ] Unit test verifies `DataValidator` rejects input violating a required-field rule
- [ ] Edge case: `CommandParser.parse("")` returns an empty parsed command without error
- [ ] Edge case: `DataNormalizer` handles None input gracefully
- [ ] `pytest tests/test_parsing_core.py -v` passes with no failures
- [ ] `ruff check` passes with no errors

---

### US-007: Restore Analysis Module Tests (file_aggregator, pattern_extractor, correlation_analyzer)

**Description:** As a developer, I want minimal test coverage for analysis modules so that regressions in file aggregation, pattern extraction, and correlation analysis are caught.

**Implementation Notes:**
- Create `tests/test_analysis_core.py` covering 3 modules: `file_aggregator.py`, `pattern_extractor.py`, `correlation_analyzer.py`
- For `file_aggregator.py` (~305 LOC): test `FileAggregator` scanning a tmp directory with sample files, verify `FileSummary` fields
- For `pattern_extractor.py` (~283 LOC): test `PatternExtractor` extracting patterns from sample text, verify `Theme` creation
- For `correlation_analyzer.py` (~238 LOC): test `CorrelationAnalyzer` finding correlations between sample data points
- Use `tmp_path` fixture to create sample files for `FileAggregator` tests
- Follow patterns in existing phase test files for class/method structure

**Acceptance Criteria:**
- [ ] Unit test verifies `FileAggregator` returns `FileSummary` objects for files in a directory
- [ ] Unit test verifies `PatternExtractor` identifies at least one pattern in sample text
- [ ] Unit test verifies `CorrelationAnalyzer` returns a result structure for correlated inputs
- [ ] Edge case: `FileAggregator` returns empty list for an empty directory
- [ ] Edge case: `PatternExtractor` returns empty patterns for empty input
- [ ] `pytest tests/test_analysis_core.py -v` passes with no failures
- [ ] `ruff check` passes with no errors

## 4. Non-Goals (Out of Scope)

- Restoring all ~590 deleted tests — we only restore minimal coverage per module
- Refactoring production code in the affected modules
- Adding integration tests or end-to-end tests
- Achieving any specific code coverage percentage target
- Modifying the existing `test_extension_lifecycle.py` or `test_networking_connection.py` files

## 5. Technical Considerations

- All new test files should follow the existing naming convention: `test_<area>_<scope>.py`
- Use `pytest` fixtures (`tmp_path`, `monkeypatch`) over manual setup/teardown
- Mock external I/O (httpx, subprocess, filesystem) to keep tests fast and deterministic
- Use `pytest-asyncio` for async test methods where the production code is async
- Keep each test file focused on one logical area to maintain the cleanup goals

## 6. Open Questions

- None — the code review findings are specific and actionable.
