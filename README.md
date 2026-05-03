# mARCH

A full Python rewrite of the Github Copilot Cli application, converting the original 13.3MB minified Node.js bundle to a modern, maintainable Python implementation.

## Status: 90% Complete (Phases 1-9 of 10)

- ✅ **Phase 1-9**: Core infrastructure, CLI, GitHub integration, code intelligence, TUI, AI agents, configuration, platform-specific features, and validation
- ⏳ **Phase 10**: Documentation & Distribution (in progress)

**Test Coverage**: 328 passing tests, 2 skipped (optional ripgrep dependency)

## Features

### Core Capabilities
- 🎯 **Slash Commands**: Full support for `/login`, `/logout`, `/model`, `/lsp`, `/feedback`, `/experimental`, `/status`, and more
- 🔐 **GitHub Integration**: PAT-based authentication with secure token storage, repository context detection, GitHub API access
- 💻 **Code Intelligence**: 
  - Tree-sitter syntax parsing (11+ languages)
  - Ripgrep code search
  - Language Server Protocol (LSP) client
  - Syntax highlighting with multiple themes
- 🖥️ **Terminal UI**: Rich-based panels, multi-window layouts, conversation rendering, ASCII art banners
- 🤖 **AI Agent System**: Claude API integration, multi-turn conversations, streaming responses, specialized code analysis
- ⚙️ **Configuration Management**: User preferences, session state persistence, LSP server configuration
- 🌐 **Platform Support**: Windows, macOS, Linux with platform-specific features:
  - Cross-platform clipboard access
  - Image processing and ASCII art rendering
  - Console detection and capabilities
  - Platform-native path handling

## Installation

### Requirements
- **Python**: 3.10+ (tested with 3.14.4)
- **pip**: For package installation

### Quick Start

```bash
# Install from source
git clone https://github.com/github/march.git
cd march
pip install -e .

# Verify installation
march-cli --version
```

### Optional Dependencies

For enhanced functionality, install optional packages:

```bash
# Claude AI integration
pip install anthropic

# Image handling
pip install Pillow

# Tree-sitter syntax parsing
pip install tree-sitter

# Code search (ripgrep)
brew install ripgrep  # macOS
apt-get install ripgrep  # Linux
choco install ripgrep  # Windows
```

## Usage

### Basic Commands

```bash
# Start interactive REPL
march

# Show version and features
march-cli --version

# Enable experimental features
march-cli --experimental

# Set log level
march-cli --log-level debug
```

### Slash Commands

Inside the interactive REPL:

```
/login                    # Authenticate with GitHub
/logout                   # Remove GitHub credentials
/model <name>            # Switch AI model
/status                  # Show system and GitHub status
/lsp <language>          # Configure language server
/help                    # Show command help
/exit or Ctrl+D          # Exit REPL
```

### Configuration

User configuration is stored in `~/.march/config.json`:

```json
{
  "model": "claude-sonnet-4.5",
  "experimental": false,
  "log_level": "INFO",
  "lsp_enabled": true
}
```

User preferences (theme, recent models) are stored in `~/.march/preferences.json`.

## Architecture

### Module Structure

```
src/mARCH/
├── __init__.py              # Package initialization
├── cli.py                   # Typer CLI framework and REPL
├── slash_commands.py        # Slash command parser
├── config.py                # Configuration management
├── state_persistence.py     # User state and preferences
├── logging_config.py        # Logging setup
├── exceptions.py            # Custom exceptions
│
├── github_auth.py           # GitHub PAT authentication
├── github_api.py            # GitHub API wrapper
├── github_context.py        # Git repo detection
├── github_integration.py     # GitHub facade
│
├── tree_sitter.py           # Syntax tree parsing
├── ripgrep_search.py        # Code search integration
├── lsp_client.py            # Language Server Protocol client
├── syntax_highlight.py      # Code syntax highlighting
├── code_intelligence.py     # Code intelligence facade
│
├── tui_conversation.py      # Message rendering
├── tui_banner.py            # Splash screens
├── tui_layout.py            # Window management
├── tui.py                   # TUI facade
│
├── agent_state.py           # Agent state machine
├── ai_client.py             # AI model integration
├── mcp_integration.py       # Model Context Protocol
│
├── platform_utils.py        # Platform detection
├── clipboard.py             # Cross-platform clipboard
├── image_utils.py           # Image processing
├── lsp_config.py            # LSP server configuration
│
└── validation.py            # Health checks and validation
```

### Design Patterns

- **Singleton Pattern**: Global managers for CLI state, configuration, GitHub, TUI, agents, etc.
- **Facade Pattern**: High-level interfaces (`CodeIntelligence`, `mARCHTUI`, `GitHubIntegration`)
- **State Machine**: Agent state management with defined transitions
- **Plugin Architecture**: MCP protocol for tool extensibility

## Configuration

### Environment Variables

```bash
# GitHub authentication
export GH_TOKEN="github_pat_..."
export GITHUB_TOKEN="github_pat_..."  # Fallback

# mARCH settings
export COPILOT_MODEL="claude-sonnet-4.5"
export COPILOT_LOG_LEVEL="DEBUG"
export COPILOT_EXPERIMENTAL="true"
```

### LSP Configuration

Language servers are configured in `~/.march/lsp-config.json`. Default servers include:
- Python (pylsp)
- JavaScript/TypeScript (typescript-language-server)
- Go (gopls)
- Rust (rust-analyzer)
- Java, C, C++, Ruby, Bash

## Development

### Testing

```bash
# Run all tests
pytest

# Run specific phase tests
pytest tests/test_phase1_foundation.py
pytest tests/test_phase2_cli.py
# ... etc for phases 3-9

# Run with coverage
pytest --cov=src/mARCH
```

### Code Quality

```bash
# Format with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type checking with mypy
mypy src/mARCH
```

### Building and Distribution

```bash
# Build package
python -m build

# Publish to PyPI (requires credentials)
twine upload dist/*
```

## Differences from JavaScript Version

### Simplified Architecture
- Removed React-based TUI in favor of Rich (simpler, smaller footprint)
- Removed complex bundling; pure Python modules
- Streamlined state management (no Redux)

### Enhanced Features
- Better cross-platform support with dedicated platform modules
- Improved configuration management with JSON + environment variables
- More flexible LSP configuration system
- Built-in system validation and health checks

### Python-Specific Advantages
- Native async/await with asyncio
- Type hints throughout
- Comprehensive test suite with pytest
- Cleaner dependency management with pip/pyproject.toml

## Troubleshooting

### GitHub Authentication Issues

```bash
# Verify token is set correctly
export GH_TOKEN="your_token"
march-cli /status

# Re-authenticate
march-cli /login
```

### LSP Not Working

```bash
# Check LSP configuration
march-cli /status  # Shows LSP status

# Install required language server
pip install pylsp  # For Python
npm install -g typescript-language-server  # For JavaScript/TypeScript
```

### Clipboard Issues (Linux)

Install clipboard manager:
```bash
sudo apt-get install xclip   # or xsel
```

## Performance

- **Startup Time**: ~500ms (Python interpreter + imports)
- **Memory Usage**: ~50-100MB base, up to 200MB with loaded code
- **Test Suite**: 328 tests in ~18 seconds

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT (same as original JavaScript version)

## Roadmap

- [ ] Phase 10: Complete documentation and package for PyPI distribution
- [ ] Plugin system for extending functionality
- [ ] Web UI dashboard
- [ ] VS Code extension integration
- [ ] Language-specific optimization
- [ ] Performance profiling and optimization

## References

- [Original JavaScript mARCH CLI](https://github.com/github/march-cli)
- [Tree-sitter Documentation](https://tree-sitter.github.io/)
- [Language Server Protocol Specification](https://microsoft.github.io/language-server-protocol/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Anthropic Claude API](https://docs.anthropic.com/)

## Support

For issues and questions:
- Check existing issues: [GitHub Issues](https://github.com/github/march/issues)
- Review documentation: See `docs/` directory
- Create a new issue with detailed information

---

**Made with ❤️ in Python**
