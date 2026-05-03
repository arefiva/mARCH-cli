.PHONY: test test-core test-extension test-networking test-quick test-forked lint fmt typecheck

# Run the full test suite (avoid from inside Copilot CLI — use per-group targets instead)
test:
	python -m pytest tests/ -v

# Core user-facing functionality — safe to run from Copilot CLI
test-core:
	python -m pytest \
		tests/test_phase1_foundation.py \
		tests/test_phase2_cli.py \
		tests/test_phase3_github.py \
		tests/test_phase0_tui_and_modes.py \
		tests/test_repl_mode_switching.py \
		-v

# Agent, config, validation, platform
test-agent:
	python -m pytest \
		tests/test_phase6_agent.py \
		tests/test_phase7_config.py \
		tests/test_phase9_validation.py \
		tests/test_phase8_platform.py \
		-v

# TUI and code intelligence
test-ui:
	python -m pytest \
		tests/test_phase5_tui.py \
		tests/test_phase4_code_intelligence.py \
		tests/test_analysis_multifile.py \
		-v

# Extension system
test-extension:
	python -m pytest \
		tests/test_extension_cli_command.py \
		tests/test_extension_contracts.py \
		tests/test_extension_discovery.py \
		tests/test_extension_integration.py \
		tests/test_extension_lifecycle.py \
		tests/test_extension_manager.py \
		tests/test_extension_manifest.py \
		tests/test_extension_protocol.py \
		tests/test_extension_registry.py \
		tests/test_extension_sandbox.py \
		tests/test_extension_tool.py \
		-v

# Networking layer
test-networking:
	python -m pytest \
		tests/test_networking_connection.py \
		tests/test_networking_http_client.py \
		tests/test_networking_payload.py \
		tests/test_networking_resilience.py \
		tests/test_networking_rpc.py \
		tests/test_networking_transport.py \
		-v

# Quickest / lightest tests — good first check during development
test-quick:
	python -m pytest \
		tests/test_phase1_foundation.py \
		tests/test_phase2_cli.py \
		tests/test_repl_mode_switching.py \
		-v

# Run full suite with each test isolated in its own subprocess (slower but memory-safe)
test-forked:
	python -m pytest tests/ --forked -v

lint:
	python -m ruff check src/ tests/

fmt:
	python -m black src/ tests/
	python -m isort src/ tests/

typecheck:
	python -m mypy src/
