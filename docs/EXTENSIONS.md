# Extension System Documentation

## Overview

The mARCH Extension System allows developers to extend the CLI with custom capabilities without modifying core code. The system provides:

- **Multiple extension types**: CLI commands, tools, MCP servers, and scripts
- **Dynamic loading/unloading**: Load extensions on-demand without restarting
- **Configurable sandboxing**: Control extension access to files, network, and resources
- **Service discovery**: Extensions can discover and communicate with each other
- **Lifecycle management**: Extensions are managed through a consistent state machine
- **Security model**: Permissions-based access control with resource limits

## Architecture

```
┌─────────────────────────────────────────────┐
│  Extension Manager (central coordinator)    │
└──────────┬──────────────────────────────────┘
           │
   ┌───────┼───────┬──────────┬───────────┐
   │       │       │          │           │
   v       v       v          v           v
Registry Lifecycle Sandbox   CLI Loader  Tool Loader
```

## Key Components

### 1. Extension Registry
- **Responsibility**: Discover and catalog available extensions
- **Location**: `src/mARCH/extension/registry.py`
- **Features**:
  - Scans standard directories (`~/.copilot/extensions/`, `.github/extensions/`)
  - Parses YAML/JSON manifests
  - Validates dependencies
  - Detects circular dependencies

### 2. Extension Lifecycle Manager
- **Responsibility**: Manage loading, initialization, and state transitions
- **Location**: `src/mARCH/extension/lifecycle.py`
- **States**: `not_loaded → loading → loaded → active → unloading → unloaded`
- **Features**:
  - Load/unload operations
  - Activation/deactivation
  - Hook system for lifecycle events
  - Automatic restart with exponential backoff
  - Health monitoring

### 3. Extension Sandbox & Security
- **Responsibility**: Control what extensions can access
- **Location**: `src/mARCH/extension/sandbox.py`, `src/mARCH/extension/permissions.py`
- **Features**:
  - Configurable sandboxing levels
  - File system access control
  - Network access whitelist
  - Resource limits (memory, CPU, file descriptors)
  - Permission declaration and validation

### 4. Extension Protocol Handler
- **Responsibility**: RPC communication between extensions and core
- **Location**: `src/mARCH/extension/protocol.py`
- **Features**:
  - JSON-RPC 2.0 message framing
  - Request/response correlation
  - Event subscription and broadcasting
  - Timeout handling

### 5. Service Registry & Discovery
- **Responsibility**: Enable inter-extension communication
- **Location**: `src/mARCH/extension/discovery.py`
- **Features**:
  - Service registration and discovery
  - Event bus for pub/sub
  - Direct RPC between extensions

### 6. Extension Manager
- **Responsibility**: Coordinate all extension systems
- **Location**: `src/mARCH/extension/manager.py`
- **Features**:
  - Unified interface for extension operations
  - Auto-load extensions on startup
  - Status tracking and reporting

## Extension Types

### CLI Command Extensions
Register new CLI commands with the mARCH CLI.

```python
from mARCH.extension.cli_command import CliCommandExtension

class MyExtension(CliCommandExtension):
    async def on_load(self):
        self.register_command("hello", self.hello_cmd)
    
    def hello_cmd(self, name: str = "World"):
        print(f"Hello, {name}!")
```

### Tool Extensions
Provide callable tools for agents and workflows.

```python
from mARCH.extension.tool import ToolExtension

class CalculatorExtension(ToolExtension):
    async def on_load(self):
        self.register_tool("add", self.add_fn)
    
    async def add_fn(self, a: float, b: float) -> float:
        return a + b
```

### MCP Server Extensions
Wrap and expose MCP (Model Context Protocol) servers.

*Implementation in progress*

### Custom Script Extensions
Load and execute Python/JavaScript/Shell scripts as extensions.

*Implementation in progress*

## Extension Manifest

All extensions require a `manifest.yaml` or `manifest.json` file:

```yaml
name: my-extension
version: 1.0.0
display_name: My Extension
description: What this extension does
author: Your Name
license: MIT

type: cli_command           # cli_command, tool, mcp_server, script
entry_point: extension.py   # Path to entry module

# Optional fields
dependencies: []            # Required extensions
required_version: ">=0.1.0" # Min mARCH version

sandbox_level: file_restricted  # none, file_restricted, process_isolated
permissions:
  - type: file_read
    resource: ~/.config/**
    description: Read config files
  - type: network_read
    resource: api.example.com
    description: Call API
```

## Permissions Model

Extensions declare required permissions in their manifest:

| Permission | Level | Description |
|-----------|-------|-------------|
| `file_read` | File System | Read files from specified paths |
| `file_write` | File System | Write files to specified paths |
| `network_read` | Network | Make requests to specified domains |
| `environment_vars` | Environment | Access environment variables |

Resource patterns:
- `/home/*` - Single level wildcard
- `/home/**` - Recursive wildcard
- `/home/user` - Exact path

## Sandboxing Levels

| Level | File Access | Network | Process Isolation | Use Case |
|-------|------------|---------|-------------------|----------|
| `none` | Full | Full | None | Trusted first-party extensions |
| `file_restricted` | Whitelisted | Whitelisted | None | Most third-party extensions |
| `process_isolated` | Whitelisted | Whitelisted | Subprocess | Untrusted extensions |

## Quick Start

### Creating an Extension

1. Create a directory: `~/.copilot/extensions/my-extension/`

2. Create `manifest.yaml`:
```yaml
name: my-extension
version: 1.0.0
display_name: My Extension
description: Example extension
type: cli_command
entry_point: extension.py
```

3. Create `extension.py`:
```python
from mARCH.extension.cli_command import CliCommandExtension
from mARCH.extension.lifecycle import ExtensionContext

class MyExtension(CliCommandExtension):
    async def on_load(self):
        self.register_command("hello", self.hello_cmd)
    
    def hello_cmd(self):
        print("Hello from my extension!")

def create_extension(context: ExtensionContext):
    return MyExtension(context)
```

### Loading an Extension

```python
from mARCH.extension.manager import ExtensionManager

manager = ExtensionManager()
await manager.initialize()
await manager.load_extension("my-extension")

# List loaded extensions
loaded = manager.list_loaded_extensions()
```

## Testing

Run the comprehensive test suite:

```bash
# Run all extension tests
pytest tests/test_extension_*.py -v

# Run specific component tests
pytest tests/test_extension_registry.py
pytest tests/test_extension_lifecycle.py
pytest tests/test_extension_sandbox.py
```

## Performance Considerations

- **Lazy loading**: Extensions are only loaded when needed
- **Async execution**: All I/O operations are non-blocking
- **Resource limits**: Process-isolated extensions have memory and CPU limits
- **Caching**: Extension manifests are cached after discovery

## Security Best Practices

1. **Always declare permissions** - Extensions should only request needed permissions
2. **Use file-restricted sandbox** - Default for third-party extensions
3. **Validate input** - Extensions should validate all inputs
4. **Avoid shell execution** - Use subprocess with explicit arguments
5. **Lock dependencies** - Use version constraints for extension dependencies

## Future Enhancements

- Extension signing and verification
- Extension marketplace/registry
- Plugin hot-reload without restart
- Resource usage profiling
- Multi-language support (Go, Rust, Node.js)
- Extension dependency management via package managers

## Contributing Extensions

To contribute an extension to mARCH:

1. Follow the extension guidelines (security, permissions, documentation)
2. Include comprehensive tests
3. Document all commands/tools and their parameters
4. Submit a PR with the extension code
5. Include usage examples

## Examples

- `src/mARCH/extension/builtin/hello_command/` - Simple CLI command extension example

## API Reference

See the generated API documentation for detailed method signatures and examples.

## Support

For issues or questions:
- Check the examples directory
- Review test files for usage patterns
- Open an issue on GitHub
