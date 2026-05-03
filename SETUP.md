# mARCH CLI Setup Guide

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Anthropic API key (get one at https://console.anthropic.com/account/keys)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/arefiva/copilot-cli-python.git
cd copilot-cli-python
```

### 2. Install Dependencies

```bash
pip install -e .
```

This installs the CLI with all required dependencies including:
- `anthropic` - For Claude API access
- `typer` - For CLI framework
- `rich` - For beautiful terminal output
- `python-dotenv` - For .env file support

## Configuration

### Method 1: Using .env File (Recommended)

The easiest way to set up your API key is using a `.env` file:

1. Copy the example configuration:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
```bash
# .env
GH_TOKEN=your_github_token_here
anthropic_api_key=your_anthropic_api_key_here
```

3. The CLI will automatically load the `.env` file on startup.

### Method 2: Environment Variables

You can also set environment variables directly:

```bash
# For Anthropic API key
export anthropic_api_key=your_api_key_here

# Or use the uppercase version
export ANTHROPIC_API_KEY=your_api_key_here

# For GitHub token
export GH_TOKEN=your_github_token_here
```

### Method 3: Interactive Setup Command

Run the CLI and use the setup command:

```bash
march-cli /setup anthropic
```

This will prompt you to enter your API key interactively and save it to the config.

## Getting Your API Keys

### Anthropic API Key

1. Go to https://console.anthropic.com/account/keys
2. Click "Create Key"
3. Copy the generated key
4. Add it to your `.env` file: `anthropic_api_key=sk-ant-...`

### GitHub Token (Optional)

1. Go to https://github.com/settings/personal-access-tokens/new
2. Create a new token with "mARCH Requests" scope
3. Copy the token
4. Add it to your `.env` file: `GH_TOKEN=github_pat_...`

## Quick Start

### Start the CLI

```bash
march
```

### Send a Prompt

Just type any prompt and press Enter:
```
> What is Python?
```

The AI will stream a response in real-time.

### Available Commands

- `/setup anthropic` - Configure Anthropic API key interactively
- `/status` - Show CLI status and configuration
- `/help` - Show available commands
- `/model` - Change AI model
- `/login` - GitHub authentication
- `/logout` - GitHub logout

## Troubleshooting

### "Could not resolve authentication method" Error

This means the API key is not being found. Check:

1. Is `.env` file present in the project directory?
2. Is `anthropic_api_key=` set correctly (not `anthropic_api_key=` with empty value)?
3. Try setting the environment variable directly:
   ```bash
   export anthropic_api_key=your_key_here
   march
   ```

### Model Not Found Error

The CLI uses Claude Opus 4.1 by default. If you get a model not found error:

1. Check your API key is valid at https://console.anthropic.com/account/keys
2. Make sure your account has access to the Claude models
3. Try a different model (future versions may support switching models)

### No Response from AI

1. Check your internet connection
2. Verify your API key is correct
3. Check if Anthropic API is down: https://status.anthropic.com/
4. Look at logs: `march --verbose` (if supported)

## Project Structure

```
copilot-cli-python/
├── src/mARCH/              # Main package
│   ├── cli/                # CLI interface
│   ├── core/               # AI client and agent logic
│   ├── config/             # Configuration management
│   ├── github/             # GitHub integration
│   └── ...                 # Other modules
├── tests/                  # Test suite
├── .env.example            # Example environment variables
├── pyproject.toml          # Project configuration
└── README.md               # Project documentation
```

## Development

### Run Tests

```bash
python -m pytest tests/ -v
```

### Type Checking

```bash
mypy src/mARCH
```

### Code Formatting

```bash
black src/mARCH tests
```

## Configuration Files

### User Configuration Directory

- **Location**: `~/.march/`
- **Config File**: `~/.march/config.json` - User preferences
- **Token Storage**: `~/.march/github_token.json` - GitHub authentication
- **Conversations**: `~/.march/conversations/` - Saved conversations
- **Sessions**: `~/.march/sessions/` - Session data

### Environment File

- **Location**: `.env` in project root
- **Format**: `KEY=value` pairs
- **Supported Keys**:
  - `anthropic_api_key` - Anthropic Claude API key
  - `ANTHROPIC_API_KEY` - Alternative environment variable name
  - `GH_TOKEN` - GitHub personal access token

## Security Notes

⚠️ **Important**: Never commit `.env` files with real API keys to version control!

The `.env` file is listed in `.gitignore` to prevent accidental commits. Make sure:
- `.env` is in `.gitignore` ✓
- `.env.example` contains only placeholder values ✓
- Real `.env` is kept locally only ✓

## Support

For issues or questions:
1. Check the README.md file
2. Review the PROJECT_STRUCTURE.md for architecture details
3. Run tests to verify installation: `pytest tests/ -q`
4. Check environment variables: `env | grep -i anthropic`

## Next Steps

1. ✓ Install dependencies: `pip install -e .`
2. ✓ Set up `.env` file with API keys
3. ✓ Start the CLI: `march`
4. ✓ Send your first prompt!

Happy coding! 🚀
