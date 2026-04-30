# mARCH Project Structure

## Overview

The mARCH CLI project follows a modular, domain-driven structure to improve maintainability and code organization.

## Directory Structure

```
src/mARCH/
├── __init__.py                    # Package initialization with lazy imports
├── exceptions.py                  # Custom exception classes
├── logging_config.py              # Logging configuration
│
├── cli/                           # CLI Interface Layer
│   ├── __init__.py
│   └── cli.py                     # Main CLI application & entry point
│
├── core/                          # Core AI & Agent Components
│   ├── __init__.py
│   ├── agent_state.py             # Agent state management & conversation history
│   ├── ai_client.py               # AI model clients (Claude, GPT)
│   └── slash_commands.py          # Slash command parsing & handling
│
├── config/                        # Configuration Management
│   ├── __init__.py
│   ├── config.py                  # Configuration manager & user settings
│   └── lsp_config.py              # Language Server Protocol configuration
│
├── github/                        # GitHub Integration
│   ├── __init__.py
│   ├── github_auth.py             # GitHub OAuth & PAT authentication
│   ├── github_api.py              # GitHub API client wrapper
│   ├── github_context.py          # Repository context detection
│   └── github_integration.py      # Unified GitHub integration interface
│
├── code_intelligence/             # Code Analysis & Intelligence Tools
│   ├── __init__.py
│   ├── code_intelligence.py       # Unified code intelligence interface
│   ├── tree_sitter.py             # Tree-sitter syntax tree integration
│   ├── syntax_highlight.py        # Code syntax highlighting
│   ├── lsp_client.py              # Language Server Protocol client
│   └── ripgrep_search.py          # Ripgrep code search integration
│
├── ui/                            # Terminal User Interface
│   ├── __init__.py
│   ├── tui.py                     # Main TUI controller
│   ├── tui_banner.py              # ASCII banner rendering
│   ├── tui_conversation.py        # Conversation display & rendering
│   ├── tui_layout.py              # UI layout management
│   └── ui.py                      # UI utilities & helpers
│
├── platform/                      # Platform-Specific Features
│   ├── __init__.py
│   ├── platform_utils.py          # Platform detection & utilities
│   ├── clipboard.py               # Cross-platform clipboard access
│   ├── image_utils.py             # Image processing & ASCII conversion
│   └── mcp_integration.py         # Model Context Protocol integration
│
├── state/                         # State Management
│   ├── __init__.py
│   ├── state_persistence.py       # Session state persistence & storage
│   └── agent.py                   # Agent wrapper & management
│
└── validation/                    # Validation & Testing Utilities
    ├── __init__.py
    └── validation.py              # Input validation & health checks
```

## Module Organization Principles

### 1. **Separation of Concerns**
   - Each module has a single, well-defined responsibility
   - Dependencies flow from lower-level to higher-level modules
   - Reduces coupling and improves testability

### 2. **Layered Architecture**
   - **Core Layer** (`core/`): AI agents and conversation logic
   - **Integration Layer** (`github/`, `code_intelligence/`): External service integration
   - **Presentation Layer** (`cli/`, `ui/`): User interaction
   - **Support Layer** (`config/`, `platform/`, `state/`): Infrastructure

### 3. **Clear Naming**
   - Module names reflect their purpose clearly
   - Related functionality grouped in subdirectories
   - Easy to locate specific features

## Import Patterns

### Public API (from package root)
```python
from mARCH.exceptions import mARCHError
from mARCH.logging_config import setup_logging
from mARCH.core.slash_commands import SlashCommandParser
```

### Internal Imports
```python
from mARCH.core.agent_state import Agent
from mARCH.github.github_integration import GitHubIntegration
from mARCH.code_intelligence.code_intelligence import CodeIntelligence
```

## Module Dependencies

```
cli/
├─ core/ (agents, commands)
├─ config/ (settings)
├─ github/ (auth, integration)
├─ code_intelligence/ (code analysis)
├─ ui/ (presentation)
└─ state/ (persistence)

github/
├─ config/ (settings)
└─ state/ (persistence)

code_intelligence/
├─ tree-sitter (external)
├─ ripgrep (external)
└─ lsp client (external)

ui/
└─ platform/ (utilities)

platform/
└─ (no internal dependencies)
```

## Adding New Features

### To add a new AI model provider:
1. Create `mARCH/core/ai_models/new_provider.py`
2. Implement the model interface from `ai_client.py`
3. Update `AIModelFactory` in `ai_client.py`

### To add a new slash command:
1. Update `mARCH/core/slash_commands.py` with command definition
2. Add handler in `mARCH/cli/cli.py`
3. Add tests in `tests/test_phase2_cli.py`

### To add platform-specific feature:
1. Create `mARCH/platform/new_feature.py`
2. Implement platform detection logic
3. Export from `mARCH/platform/__init__.py`

## Testing Structure

```
tests/
├── test_phase1_foundation.py      # Exceptions, logging, config
├── test_phase2_cli.py             # CLI & slash commands
├── test_phase3_github.py          # GitHub integration
├── test_phase4_code_intelligence.py # Code analysis tools
├── test_phase5_tui.py             # UI components
├── test_phase6_agent.py           # AI agents
├── test_phase7_config.py          # Configuration
├── test_phase8_platform.py        # Platform features
└── test_phase9_validation.py      # Validation & integration
```

## Performance Considerations

### Lazy Loading
- Submodules use lazy imports to reduce startup time
- Only loaded when actually used

### Circular Dependency Prevention
- Package `__init__.py` uses `__getattr__` for lazy loading
- Avoids circular import issues

## Maintenance Guidelines

1. **Keep modules focused**: Each module should do one thing well
2. **Update imports consistently**: When moving files, update all references
3. **Follow naming conventions**: Use clear, descriptive names
4. **Document dependencies**: Explain why modules depend on each other
5. **Test coverage**: Write tests for new modules before implementation

## File Size Considerations

Average module sizes:
- Small modules (< 2KB): Utilities, simple parsers
- Medium modules (2-8KB): Core logic, API clients
- Large modules (> 8KB): Complex orchestration

## Refactoring Tips

- Use IDE refactoring tools to rename/move files (handles imports automatically)
- Run full test suite after restructuring
- Verify mypy type checking passes
- Update documentation when changing structure

---

Last Updated: 2026-04-30
