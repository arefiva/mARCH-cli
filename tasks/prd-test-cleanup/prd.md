# PRD: Test Suite Optimization - Reduce Memory Footprint

## 1. Introduction/Overview

The test suite has grown to 813+ tests across 31 files, causing severe memory issues when agents or developers run the full suite. This causes:
- Memory spikes to 100% when running `pytest`
- Context window explosion in agent sessions
- Extremely long test collection times (1.07 seconds just to collect)
- Inability to work on code without triggering memory warnings

The goal is to identify and safely remove redundant, overlapping, or low-value tests while maintaining critical coverage of core functionality.

## 2. Goals

- ✅ Reduce test suite from 813+ to ~200-300 core tests (60-70% reduction)
- ✅ Maintain coverage of critical functionality: CLI, mode switching, plan mode
- ✅ Identify and remove duplicate/overlapping test scenarios
- ✅ Keep memory footprint under 50MB when loading tests
- ✅ Achieve <0.5s test collection time
- ✅ Document rationale for each major test file removal

## 3. Analysis: Test Categories

### Bloat Categories (High Priority for Removal)

**A. Phase-Based Redundancy (test_phase*.py files)**
- 9 phase files: test_phase0-9 covering same features multiple ways
- test_phase1_task3.py: 31KB, 46 tests (likely duplicates phase1_foundation)
- test_phase1_phase2.py: 16KB, 47 tests (combines phase 1&2 redundantly)
- Pattern: Each phase retests entire codebase incrementally
- **Recommendation**: Keep phase0, remove phase1-9 duplicates

**B. Networking Tests (test_networking_*.py files)**
- 6 networking files: connection, transport, rpc, payload, resilience, http_client
- 151 tests total across ~50KB
- These test internal networking abstractions rarely used by end users
- Pattern: Low-level infrastructure, tested indirectly by higher-level tests
- **Recommendation**: Keep only networking_connection (21 tests), remove others

**C. Extension Tests (test_extension_*.py files)**
- 11 extension files: sandbox, registry, protocol, lifecycle, manifest, discovery, etc.
- 237 tests total across ~60KB
- Extensions are optional/advanced feature
- Pattern: Deeply nested, testing internal plumbing vs. user-facing behavior
- **Recommendation**: Keep only extension_lifecycle (7 tests), remove others

**D. Config Tests (test_phase7_config.py)**
- 44 tests, 23KB
- Tests configuration management (env variables, file parsing, etc.)
- Low risk code path, rarely breaks
- **Recommendation**: Reduce to 5-10 core config tests

### Core Categories (Keep Most/All)

**E. CLI Tests (test_phase2_cli.py, test_phase1_foundation.py)**
- Essential user-facing functionality
- Mode switching, command parsing, help text
- **Recommendation**: Keep all 50+ tests

**F. GitHub Integration (test_phase3_github.py)**
- 19 tests, important for production use
- **Recommendation**: Keep all tests

**G. Code Intelligence (test_phase4_code_intelligence.py)**
- 38 tests, core feature
- **Recommendation**: Keep all tests

**H. TUI Tests (test_phase5_tui.py, test_phase0_tui_and_modes.py)**
- 98 tests total (66+32)
- User-facing terminal UI
- **Recommendation**: Keep phase0 (32 tests), consolidate phase5 → 20 core tests

**I. Agent Tests (test_phase6_agent.py)**
- 54 tests, AI agent core logic
- **Recommendation**: Keep 25 core tests, remove edge cases

## 4. Proposed Cleanup Strategy

### Phase 1: Identify Core Test Files (Keep 100%)
- test_phase1_foundation.py (8 tests)
- test_phase2_cli.py (20 tests)
- test_phase3_github.py (19 tests)
- test_phase4_code_intelligence.py (38 tests)
- test_phase0_tui_and_modes.py (32 tests)
- **Subtotal: 117 core tests** ✅

### Phase 2: Reduce High-Volume Files (Keep 30-50%)
- test_phase5_tui.py: 66 → 20 tests (keep main UI flow, remove edge cases)
- test_phase6_agent.py: 54 → 25 tests (keep decision logic, remove variations)
- test_phase7_config.py: 44 → 10 tests (keep config loading, remove env var edge cases)
- test_phase8_platform.py: 47 → 15 tests (keep OS-specific paths, remove other edge cases)
- test_phase9_validation.py: 31 → 10 tests (keep core validators, remove format tests)
- **Subtotal: 80 tests** ✅

### Phase 3: Remove/Consolidate Architectural Tests
- test_phase1_phase2.py: DELETE (duplicates phase1_foundation + phase2_cli)
- test_phase1_task3.py: DELETE (41KB monster, duplicates earlier phases)
- test_tui_enhancements.py: DELETE (27 tests, non-critical enhancements)
- test_analysis_multifile.py: DELETE (14KB, edge case analysis)
- **Total removed: ~140 tests** ✅

### Phase 4: Remove Infrastructure Tests (Non-User-Facing)
- test_networking_*.py: Remove 5 of 6 (keep only connection)
  - networking_connection.py: KEEP (21 tests)
  - networking_rpc.py: DELETE (32 tests)
  - networking_transport.py: DELETE (28 tests)
  - networking_payload.py: DELETE (22 tests)
  - networking_resilience.py: DELETE (26 tests)
  - networking_http_client.py: DELETE (keep in connection or remove)
  - **Total removed: ~129 tests** ✅

- test_extension_*.py: Remove 10 of 11 (keep only lifecycle)
  - extension_lifecycle.py: KEEP (7 tests)
  - extension_sandbox.py: DELETE (25 tests)
  - extension_registry.py: DELETE (20 tests)
  - extension_manifest.py: DELETE (19 tests)
  - extension_protocol.py: DELETE (19 tests)
  - extension_discovery.py: DELETE (17 tests)
  - extension_contracts.py: DELETE (13 tests)
  - extension_integration.py: DELETE (12 tests)
  - extension_cli_command.py: DELETE (11 tests)
  - extension_tool.py: DELETE (8 tests)
  - extension_manager.py: DELETE (6 tests)
  - **Total removed: ~210 tests** ✅

### Phase 5: Special Cases
- test_networking_http_client.py: 10 tests → Can be merged into networking_connection
- conftest.py: Keep (required by pytest)

## 5. Expected Outcome

**Before:**
- 813 tests across 31 files
- ~50KB context per test run
- Collection time: 1.07s
- Memory spike: 100%

**After:**
- ~220 tests across 8 files
- ~8KB context per test run
- Collection time: <0.2s
- Memory spike: <10%

**Reduction**: 73% fewer tests, 85% less memory

## 6. Implementation Approach

### US-001: Delete Low-Value Test Files
Delete 20 test files outright:
- test_phase1_phase2.py (delete redundant combination)
- test_phase1_task3.py (delete 31KB monster)
- test_tui_enhancements.py (delete non-critical)
- test_analysis_multifile.py (delete edge case)
- test_networking_rpc.py, transport, payload, resilience (delete infra)
- test_extension_sandbox, registry, manifest, protocol, discovery, contracts, integration, cli_command, tool, manager (delete 10 extension files)

### US-002: Consolidate and Reduce Core Files
Reduce test count in core files:
- test_phase5_tui.py: 66 → 20 (keep main flows, remove variations)
- test_phase6_agent.py: 54 → 25 (keep logic, remove edge cases)
- test_phase7_config.py: 44 → 10 (keep core config load)
- test_phase8_platform.py: 47 → 15 (keep platform detection)
- test_phase9_validation.py: 31 → 10 (keep validators)

### US-003: Test the Cleanup
- Verify remaining ~220 tests still pass
- Verify core CLI/plan mode functionality still works
- Verify collection time <0.2s
- Verify memory usage <10% during test run

## 7. Risk Mitigation

**What could go wrong?**
- We delete tests that actually catch bugs
- Response: Keep tests for user-facing features (CLI, TUI, GitHub, agent)

**How to validate?**
- Before deletion: Run full suite to ensure passing
- After deletion: Run remaining tests
- Spot check: Ensure critical paths have coverage
- Monitor: Track if bugs appear in deleted code paths post-cleanup

## 8. Non-Goals

- Adding new test coverage
- Refactoring tests to be "better"
- Converting to different test framework
- Achieving 100% code coverage
