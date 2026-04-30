# mARCH CLI Usage Guide

The mARCH CLI is now fully functional with AI agent support for processing user prompts and generating responses.

## Quick Start

### 1. Set Your API Key

Before using mARCH, you need to set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or create a `.env` file in your project directory:

```
ANTHROPIC_API_KEY=your-api-key-here
```

### 2. Start the Interactive CLI

```bash
march
```

You'll see the mARCH banner and be ready to interact:

```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║          GitHub mARCH CLI - Python Edition            ║
║                                                          ║
║   AI-powered coding assistant in your terminal          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

### 3. Send Prompts to the AI

Simply type your question or request and press Enter:

```
march> What is Python?
mARCH: Python is a powerful, interpreted programming language...
```

The AI will stream its response in real-time, updating as tokens are generated.

## Features

### AI Chat
- **Real-time streaming responses**: Watch responses appear character-by-character
- **Conversation memory**: All messages in your session are remembered
- **Multiple models**: Switch between claude-sonnet-4.5, claude-sonnet-4, gpt-5.4, and more
- **Temperature control**: Adjust creativity with temperature settings (0.0-2.0)

### Slash Commands
Use these special commands during your session:

- `/login` - Authenticate with GitHub
- `/logout` - Log out from GitHub
- `/model [name]` - View or change the AI model
- `/lsp` - View Language Server Protocol configuration
- `/status` - Show current status and settings
- `/experimental` - Toggle experimental mode
- `/feedback` - Send feedback
- `/help` - Show available commands

### Command-line Flags

```bash
march --help              # Show help message
march --version           # Show version
march --banner            # Show ASCII art banner
march --model claude-3    # Specify AI model
march --experimental      # Enable experimental features
march --log-level debug   # Set logging level (DEBUG, INFO, WARNING, ERROR)
```

## Examples

### Example 1: Basic Question

```
march> How do I create a Python virtual environment?
mARCH: To create a Python virtual environment, use the venv module:
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

### Example 2: Code Review

```
march> Review this Python function and suggest improvements:
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

mARCH: This function works, but here are some improvements:
1. Use list comprehension for cleaner code
2. Add type hints
3. Add documentation...
```

### Example 3: Using Slash Commands

```
march> /model
Current Model: claude-sonnet-4.5

Available Models:
  - claude-sonnet-4.5 (default)
  - claude-sonnet-4
  - gpt-5.4

Tip: Use '/model <model-name>' to change

march> /model claude-sonnet-4
✓ Model changed to: claude-sonnet-4

march> Now let me ask something with the new model...
mARCH: [Response from claude-sonnet-4]
```

## Configuration

### Configuration Files

mARCH stores configuration in `~/.march/`:

- `config.json` - Main configuration
- `preferences.json` - User preferences (theme, model, etc.)
- `lsp-config.json` - Language Server Protocol configuration
- `github_token.json` - GitHub authentication token

### Setting Model and Options

You can set default preferences in `~/.march/config.json`:

```json
{
  "model": "claude-sonnet-4.5",
  "experimental": false,
  "settings": {
    "show_banner": true,
    "theme": "default"
  }
}
```

## Troubleshooting

### "AI client not available" Error

This means the `ANTHROPIC_API_KEY` environment variable is not set.

**Solution:**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
march
```

### API Key Authentication Error

This typically means your API key is invalid or expired.

**Solution:**
1. Get a new API key from https://console.anthropic.com
2. Update your environment variable:
   ```bash
   export ANTHROPIC_API_KEY="new-key-here"
   ```

### Slow Response Times

The first request might be slower as the AI service initializes.

**Tips:**
- Keep your prompts concise
- Use `/model` to try a faster model if available
- Check your internet connection

## Advanced Usage

### Experimental Mode

Enable experimental features:

```
march> /experimental
✓ Experimental mode enabled

Experimental Features:
  - Autopilot mode: Press Shift+Tab to cycle modes
  - Auto-planning and execution
```

### GitHub Integration

Authenticate with GitHub to enable repository context:

```
march> /login
[Opens GitHub authentication flow]

march> /status
GitHub Authentication: ✓ username
Current Repository: owner/repo (clean, branch: main)
```

## Tips and Best Practices

1. **Be specific**: More detailed prompts get better responses
2. **Use context**: Provide code samples or error messages
3. **Break it down**: For complex tasks, ask step-by-step questions
4. **Save conversations**: Copy important responses to a file
5. **Experiment**: Try different models and temperature settings

## Exit the CLI

Use any of these commands to exit:

```
march> exit
march> quit
march> :q
march> q!
```

Or press `Ctrl+C` for keyboard interrupt (then use `exit` to quit cleanly).

---

For more information, visit the mARCH GitHub repository or check `/help` in the CLI.
