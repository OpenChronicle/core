# Contributing to OpenChronicle

Thank you for your interest in contributing to OpenChronicle! This document provides guidelines for contributing to the project.

## Development Workflow

### Prerequisites
- Python 3.11+
- Git
- Basic understanding of hexagonal architecture

### Setup
```bash
# Clone and setup
git clone https://github.com/OpenChronicle/openchronicle-core.git
cd openchronicle-core

# Create virtual environment
python -m venv openchronicle-env
openchronicle-env\Scripts\activate  # Windows
# source openchronicle-env/bin/activate  # Linux/Mac

# Install development dependencies
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install
```

### Development Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run Quality Checks**
   ```bash
   # Linting and formatting
   ruff check .
   black --check .
   mypy .

   # Tests with coverage
   pytest --cov=src --cov-fail-under=85

   # Or use make commands
   make lint
   make test
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

5. **Submit Pull Request**
   - Push to your feature branch
   - Create PR with clear description
   - Address review feedback

## Coding Standards

### Python Style
- **Formatting**: Black (88 character line length)
- **Linting**: Ruff with project configuration
- **Import Sorting**: isort via ruff
- **Type Hints**: Required for all public APIs

### Code Organization
- **Imports**: Always use absolute imports (`from openchronicle.domain import...`)
- **Architecture**: Follow hexagonal architecture patterns
- **Dependencies**: Domain → Application → Infrastructure
- **Testing**: Mirror source structure in `tests/`

### Docstrings
Use Google-style docstrings for all public modules, classes, and functions:

```python
def process_story(story_id: str, options: dict) -> StoryResult:
    """Process a story with given options.
    
    Args:
        story_id: Unique identifier for the story
        options: Processing configuration options
        
    Returns:
        StoryResult: Processed story data and metadata
        
    Raises:
        StoryNotFoundError: If story_id doesn't exist
        ValidationError: If options are invalid
    """
```

## Testing Guidelines

### Test Structure
- **Unit Tests**: `tests/unit/` - Test individual modules
- **Integration Tests**: `tests/integration/` - Test module interactions  
- **E2E Tests**: `tests/e2e/` - Test complete workflows

### Test Requirements
- Maintain 85% minimum coverage
- Use descriptive test names
- Include both positive and negative test cases
- Mock external dependencies appropriately

### Example Test
```python
def test_story_processing_with_valid_input():
    """Test story processing succeeds with valid input."""
    # Arrange
    story_id = "test-story-123"
    options = {"theme": "adventure"}
    
    # Act
    result = process_story(story_id, options)
    
    # Assert
    assert result.success is True
    assert result.story_id == story_id
```

## Commit Message Format

Use conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(model): add support for new LLM provider
fix(memory): resolve race condition in memory updates
docs(readme): update installation instructions
```

## Architecture Guidelines

### Current Migration
The project is migrating from dual architecture to unified hexagonal architecture:
- **Legacy**: `core/` modules (being phased out)  
- **Modern**: `src/openchronicle/` hexagonal structure

### Contribution Areas
- **Phase 0 Tasks**: Security tools, documentation, logging
- **Phase 1 Tasks**: Legacy migration assistance
- **Testing**: Enhance test coverage and quality
- **Documentation**: Keep docs current and accurate

### Dependency Rules
- Domain layer: No external dependencies
- Application layer: Depends only on domain interfaces
- Infrastructure layer: Implements domain interfaces
- Interface layer: Coordinates application services

## Getting Help

- **Development Plan**: See `docs/DEVELOPMENT_PLAN.md`
- **Architecture**: See `docs/ARCHITECTURE.md`
- **Current Status**: See `.copilot/project_status.json`
- **Phase Tasks**: See `.copilot/PHASE_0_DETAILED_TASKS.md`

## Code of Conduct

- Be respectful and professional
- Focus on constructive feedback
- Embrace breaking changes for better architecture
- Prioritize code quality and maintainability

## Questions?

If you have questions about contributing, please:
1. Check existing documentation
2. Review current issues and PRs
3. Ask in discussions or create an issue

Thank you for contributing to OpenChronicle!
