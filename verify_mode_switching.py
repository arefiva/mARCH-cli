#!/usr/bin/env python3
"""Minimal verification script for US-001 mode switching fix.

This is NOT a pytest test file to avoid loading 813+ tests.
Run directly: python verify_mode_switching.py
"""

import sys

from mARCH.cli.repl import MARCH_REPL, ModeChangeSignal
from mARCH.core.execution_mode import ExecutionMode, ModeManager


def test_basic_init():
    """Test 1: REPL initializes with flag."""
    mode_manager = ModeManager(initial_mode=ExecutionMode.INTERACTIVE)
    repl = MARCH_REPL(mode_manager=mode_manager)
    assert repl._pending_mode_change is None
    print("✅ Test 1: REPL initializes correctly")


def test_mode_cycle():
    """Test 2: Mode manager cycles correctly."""
    mm = ModeManager(initial_mode=ExecutionMode.INTERACTIVE)

    # INTERACTIVE → PLAN
    new_mode = mm.cycle_mode()
    assert new_mode == ExecutionMode.PLAN

    # PLAN → AUTOPILOT
    new_mode = mm.cycle_mode()
    assert new_mode == ExecutionMode.AUTOPILOT

    # AUTOPILOT → INTERACTIVE
    new_mode = mm.cycle_mode()
    assert new_mode == ExecutionMode.INTERACTIVE

    print("✅ Test 2: Mode cycling works correctly")


def test_mode_change_signal_backward_compat():
    """Test 3: ModeChangeSignal still exists."""
    signal = ModeChangeSignal(ExecutionMode.PLAN)
    assert signal.new_mode == ExecutionMode.PLAN
    assert "plan" in str(signal)
    print("✅ Test 3: ModeChangeSignal backward compatibility OK")


def test_key_binding_no_exception():
    """Test 4: Key binding sets flag without exception."""
    mode_manager = ModeManager(initial_mode=ExecutionMode.INTERACTIVE)
    repl = MARCH_REPL(mode_manager=mode_manager)

    # Get key bindings
    kb = repl._create_key_bindings()

    # Find Shift+Tab handler
    shift_tab_handler = None
    for binding in kb.bindings:
        if "s-tab" in str(binding.keys):
            shift_tab_handler = binding.handler
            break

    assert shift_tab_handler is not None, "Shift+Tab binding not found"

    # Call handler - should NOT raise exception
    try:
        from unittest.mock import Mock
        mock_event = Mock()
        shift_tab_handler(mock_event)
        assert repl._pending_mode_change == ExecutionMode.PLAN
        print("✅ Test 4: Shift+Tab sets flag without exception")
    except Exception as e:
        print(f"❌ Test 4 FAILED: {e}")
        return False

    return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("VERIFYING US-001: Mode Switching Fix")
    print("=" * 60)
    print()

    try:
        test_basic_init()
        test_mode_cycle()
        test_mode_change_signal_backward_compat()
        if not test_key_binding_no_exception():
            return 1

        print()
        print("=" * 60)
        print("✅ ALL VERIFICATION CHECKS PASSED")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
