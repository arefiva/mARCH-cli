# Contributing to GitHub Copilot CLI (Python)

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Getting Started

### Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/march.git
cd march
git remote add upstream https://github.com/github/march.git
```

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### Creating a Feature Branch

```bash
# Update main
git fetch upstream
git checkout main
git rebase upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_phase1_foundation.py

# Run with coverage
pytest --cov=src/mARCH

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/ --fix

# Type check with mypy
mypy src/mARCH
```

### Committing Changes

```bash
# Follow conventional commits
git commit -m "feat: add new feature description"
git commit -m "fix: resolve issue with xyz"
git commit -m "docs: update README"
git commit -m "test: add tests for new feature"
```

## Pull Request Process

1. **Keep PRs focused**: One feature or fix per PR
2. **Update tests**: Add tests for new functionality
3. **Update docs**: Update relevant documentation
4. **Write clear description**: Explain what and why
5. **Request review**: Tag maintainers for review
6. **Address feedback**: Make requested changes
7. **Squash commits**: Clean up history before merge

### PR Description Template

```markdown
## Description
Brief description of changes

## Related Issue
Fixes #123 (if applicable)

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Existing tests pass
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] No new warnings generated
- [ ] Documentation updated
- [ ] Comments added for complex logic
```

## Architecture Guidelines

### Module Organization

```
src/mARCH/
├── Core modules (cli, config, logging, exceptions)
├── Feature modules (github_*, code_*, tui_*)
├── Utilities (platform_*, clipboard, image_*, validation)
└── Main facades (github_integration, code_intelligence, tui)
```

### Design Patterns

1. **Singleton Pattern**: For global managers
2. **Facade Pattern**: High-level interfaces
3. **State Machine**: For agent state
4. **Composition**: Over inheritance

### Code Style

- **Python Version**: 3.10+ (use modern syntax)
- **Type Hints**: Required for all functions
- **Docstrings**: Module, class, and method level
- **Max Line Length**: 100 characters
- **Imports**: Alphabetically organized, grouped by type

### Example Module Structure

```python
"""
Module description and purpose.

Key components:
- ComponentA: Description
- ComponentB: Description
"""

from typing import Optional
from dataclasses import dataclass

from exceptions import CopilotError


@dataclass
class MyClass:
    """Class description."""
    
    field: str
    
    def method(self) -> str:
        """Method description."""
        return self.field
```

## Testing Guidelines

### Test Organization

```
tests/
├── test_phase1_foundation.py
├── test_phase2_cli.py
├── ...
└── test_phase9_validation.py
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch

class TestFeature:
    """Test feature description."""
    
    def test_basic_functionality(self):
        """Test basic behavior."""
        # Arrange
        obj = MyClass("test")
        
        # Act
        result = obj.method()
        
        # Assert
        assert result == "test"
    
    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ValueError):
            MyClass("")
    
    @patch('module.external_call')
    def test_with_mock(self, mock_call):
        """Test with mocking."""
        mock_call.return_value = "mocked"
        # Test code
```

### Test Expectations

- **Coverage**: Aim for 80%+ coverage
- **Isolation**: Tests should be independent
- **Performance**: Tests should run quickly
- **Clarity**: Test names should be descriptive

## Documentation Guidelines

### README Updates

- Keep installation instructions current
- Update feature list when adding features
- Add troubleshooting for common issues
- Include examples for new functionality

### Code Comments

- Explain *why*, not *what*
- Use for complex logic only
- Keep comments in sync with code
- Avoid over-commenting

### Docstrings

```python
def function(arg1: str, arg2: int) -> str:
    """
    Brief one-line description.
    
    Longer description if needed. Can span
    multiple lines.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When something is invalid
        TypeError: When type is wrong
    """
    pass
```

## Release Process

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Creating a Release

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.2.3`
4. Push to main: `git push upstream main --tags`
5. Build package: `python -m build`
6. Upload to PyPI: `twine upload dist/*`

## Reporting Issues

### Bug Reports

Include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages or logs

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative approaches
- Example usage

## Code Review Process

### For Reviewers

- Check code quality and style
- Verify tests cover changes
- Ensure documentation is updated
- Consider edge cases and error handling
- Provide constructive feedback

### For Authors

- Respond to all comments
- Explain design decisions
- Be open to suggestions
- Request re-review after changes

## Questions?

- Open an issue with the `question` label
- Join our discussions
- Email maintainers

Thank you for contributing! 🎉
