# Contributing to Sensor Data Collector

Thank you for your interest in contributing to the Sensor Data Collector project! This document provides guidelines and instructions for contributing.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Review Process](#review-process)
- [Community](#community)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. We expect everyone to:

- Be respectful and considerate
- Welcome newcomers and help them learn
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling or insulting remarks
- Public or private harassment
- Publishing others' private information
- Any conduct that would be considered inappropriate in a professional setting

### Enforcement

Violations of this Code of Conduct should be reported to the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Git** installed and configured
2. **Python 3.9+** installed
3. **GitHub account** with SSH or HTTPS access
4. **Code editor** (VS Code, PyCharm, etc.)
5. Basic knowledge of:
   - Python and async/await
   - FastAPI
   - REST APIs
   - Git workflow

### Development Setup

See the [Development Guide](docs/DEVELOPMENT.md#development-setup) for detailed setup instructions.

**Quick setup:**

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR-USERNAME/sensor-data-collector.git
cd sensor-data-collector/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example.txt .env
# Edit .env with your settings

# Run development server
uvicorn app.main:app --reload
```

---

## How to Contribute

### Areas for Contribution

We welcome contributions in these areas:

#### 1. Code Contributions
- **New Sensor Types** - Add support for additional sensors
- **Bug Fixes** - Fix reported issues
- **Features** - Implement planned features
- **Performance** - Optimize existing code
- **Refactoring** - Improve code quality

#### 2. Documentation
- **Improve Existing Docs** - Clarify, expand, or correct
- **Add Examples** - More code examples and tutorials
- **Translations** - Translate docs to other languages
- **Video Tutorials** - Create video guides

#### 3. Testing
- **Unit Tests** - Add test coverage
- **Integration Tests** - Test component interactions
- **Sensor Simulators** - Create test fixtures
- **Load Testing** - Test performance under load

#### 4. Design
- **UI/UX** - Frontend design (when implemented)
- **Diagrams** - Architecture diagrams
- **Icons/Logos** - Visual assets

#### 5. DevOps
- **CI/CD** - GitHub Actions workflows
- **Docker** - Improve containerization
- **Deployment Scripts** - Automation tools
- **Monitoring** - Setup guides for monitoring tools

### Good First Issues

Look for issues labeled:
- `good first issue` - Beginner-friendly
- `help wanted` - Need community help
- `documentation` - Documentation improvements
- `bug` - Bug fixes

---

## Development Workflow

### 1. Find or Create an Issue

**Before starting work:**

1. **Check existing issues** - Avoid duplicate work
2. **Create an issue** if one doesn't exist
3. **Discuss your approach** in the issue comments
4. **Wait for approval** for major changes

**Issue template:**

```markdown
## Description
Brief description of the issue or feature

## Current Behavior
What currently happens (for bugs)

## Expected Behavior
What should happen

## Proposed Solution
Your approach to solving this

## Additional Context
Any relevant information
```

### 2. Fork and Branch

```bash
# Fork the repository on GitHub

# Clone your fork
git clone https://github.com/YOUR-USERNAME/sensor-data-collector.git
cd sensor-data-collector

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL-OWNER/sensor-data-collector.git

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

**Branch Naming:**
- `feature/add-water-quality-sensor` - New features
- `fix/sensor-connection-timeout` - Bug fixes
- `docs/improve-api-reference` - Documentation
- `refactor/simplify-csv-conversion` - Refactoring
- `test/add-sensor-manager-tests` - Tests

### 3. Make Changes

**Best practices:**

- **Small, focused commits** - One logical change per commit
- **Clear commit messages** - Follow convention below
- **Follow code style** - Match existing code
- **Add tests** - For new features and bug fixes
- **Update docs** - Keep documentation current
- **Run locally** - Test your changes

### 4. Commit Messages

**Format:**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Code formatting (no logic change)
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance tasks

**Examples:**

```
feat(sensors): add water quality sensor support

- Add WaterQualitySensorService
- Add API endpoints for water quality sensors
- Update sensor manager to handle new type
- Add data models and CSV conversion

Closes #123
```

```
fix(polling): prevent scheduler job duplication

Fixed issue where turning a sensor on/off multiple times
would create duplicate polling jobs, causing excessive API calls.

Added job_id uniqueness check before creating jobs.

Fixes #456
```

```
docs(api): add examples for all endpoints

Added request/response examples for every API endpoint
to improve developer experience.
```

### 5. Keep Branch Updated

```bash
# Fetch upstream changes
git fetch upstream

# Rebase on main
git rebase upstream/main

# If conflicts, resolve and continue
git add .
git rebase --continue

# Force push to your fork (only for your branches!)
git push origin feature/your-feature-name --force
```

### 6. Run Tests and Checks

```bash
# Run tests (when available)
pytest

# Check code style
black app/ --check
flake8 app/

# Type checking
mypy app/

# Test locally
uvicorn app.main:app --reload
# Manually test your changes
```

---

## Coding Standards

### Python Style Guide

**Follow PEP 8 with these specifics:**

- **Line Length:** 88 characters (Black default)
- **Indentation:** 4 spaces (no tabs)
- **Quotes:** Double quotes for strings
- **Imports:** Grouped and sorted (standard lib, third-party, local)
- **Type Hints:** Required for all functions and methods
- **Docstrings:** Google style for public functions

**Example:**

```python
"""
Module docstring explaining purpose.
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class MyClass:
    """
    Brief class description.
    
    Longer explanation if needed.
    
    Attributes:
        attr1: Description of attr1
        attr2: Description of attr2
    """
    
    def __init__(self, attr1: str, attr2: int):
        """Initialize MyClass."""
        self.attr1 = attr1
        self.attr2 = attr2
    
    def my_method(self, param: str) -> Optional[dict]:
        """
        Brief description of method.
        
        Longer explanation if needed.
        
        Args:
            param: Description of parameter
            
        Returns:
            Description of return value
            
        Raises:
            ValueError: When param is invalid
        """
        if not param:
            raise ValueError("param cannot be empty")
        
        return {"result": param}
```

### Code Organization

- **One class per file** (generally)
- **Related functions grouped together**
- **Constants at top of file**
- **Private functions prefixed with underscore**
- **Clear separation of concerns**

### Error Handling

- **Always catch specific exceptions**
- **Provide helpful error messages**
- **Log errors appropriately**
- **Clean up resources in finally blocks**

```python
# Good
try:
    response = await client.get(url)
    response.raise_for_status()
except httpx.ConnectError as e:
    logger.error("Connection failed: %s", str(e))
    raise
except httpx.TimeoutException:
    logger.warning("Request timed out")
    return default_value

# Bad
try:
    response = await client.get(url)
except Exception:
    pass  # Silent failure
```

---

## Testing Guidelines

### Writing Tests

**Test structure:**

```python
import pytest
from unittest.mock import Mock, AsyncMock


def test_function_name():
    """Test description."""
    # Arrange
    input_data = create_test_data()
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_value


@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    # Mock async dependencies
    mock_client = AsyncMock()
    mock_client.get.return_value = Mock(
        status_code=200,
        json=lambda: {"data": "test"}
    )
    
    # Test
    result = await async_function(mock_client)
    
    # Verify
    assert result["data"] == "test"
    mock_client.get.assert_called_once()
```

### Test Coverage

- **Aim for 80%+ coverage** for new code
- **Test happy paths** and error cases
- **Test edge cases** and boundary conditions
- **Mock external dependencies** (HTTP calls, etc.)

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_sensor_manager.py

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_sensor_manager.py::test_add_sensor
```

---

## Documentation

### When to Update Documentation

**Always update docs when you:**
- Add a new feature
- Change an API endpoint
- Modify configuration options
- Fix a bug that was unclear from docs
- Add a new sensor type

### Documentation Files

| File | Update When |
|------|-------------|
| `README.md` | Major features, architecture changes |
| `docs/API.md` | API endpoint changes |
| `docs/ARCHITECTURE.md` | Design changes, new patterns |
| `docs/DEPLOYMENT.md` | Deployment process changes |
| `docs/DEVELOPMENT.md` | Development workflow changes |
| `CHANGELOG.md` | Any user-visible change |

### Documentation Style

- **Clear and concise** - Short sentences
- **Examples** - Show, don't just tell
- **Code blocks** - Use proper syntax highlighting
- **Complete** - Don't assume knowledge
- **Current** - Keep in sync with code

---

## Submitting Changes

### Pull Request Process

1. **Complete your changes**
   - All tests passing
   - Code formatted
   - Documentation updated
   - Commits clean and well-described

2. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request**
   - Go to GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out PR template (see below)

4. **Address review feedback**
   - Make requested changes
   - Push additional commits
   - Respond to comments

5. **Merge**
   - Maintainer will merge when approved
   - Delete your branch after merge

### Pull Request Template

```markdown
## Description
Brief description of changes

## Related Issue
Closes #123

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
How has this been tested?

- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
Add screenshots to help explain your changes

## Additional Context
Add any other context about the pull request here
```

---

## Review Process

### What Reviewers Look For

- **Code quality** - Clean, readable, maintainable
- **Correctness** - Does it work as intended?
- **Tests** - Adequate test coverage
- **Documentation** - Is it documented?
- **Style** - Follows project conventions
- **Performance** - No obvious performance issues
- **Security** - No security vulnerabilities

### Addressing Feedback

- **Be receptive** - Reviews help improve code
- **Ask questions** - If feedback is unclear
- **Explain decisions** - If you disagree, explain why
- **Make changes** - Address all review comments
- **Push updates** - No need to force push during review

### Review Timeline

- **Initial response** - Within 48 hours
- **Full review** - Within 1 week
- **Follow-up** - Within 48 hours of updates

---

## Community

### Communication Channels

- **GitHub Issues** - Bug reports, feature requests
- **GitHub Discussions** - Questions, ideas
- **Pull Requests** - Code review, collaboration

### Getting Help

**If you're stuck:**

1. Check documentation
2. Search existing issues
3. Ask in Discussions
4. Open an issue for clarification

**When asking for help:**

- Provide context
- Show what you've tried
- Include error messages
- Share relevant code

### Recognition

Contributors will be:
- Listed in CHANGELOG.md
- Credited in release notes
- Mentioned in project documentation (if desired)

---

## License

By contributing to Sensor Data Collector, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you have questions about contributing, please:
1. Check this guide
2. Review the [Development Guide](docs/DEVELOPMENT.md)
3. Open an issue
4. Ask in Discussions

**Thank you for contributing!** 🎉

---

**Last Updated:** January 2026  
**Maintained by:** Sensor Data Collector Team

