# Contributing to falk

Thank you for your interest in contributing to falk! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Issues

- **Search first**: Check if the issue already exists
- **Be specific**: Include error messages, OS, Python version, and steps to reproduce
- **Use templates**: Follow the issue template when creating new issues

### Suggesting Features

- **Check discussions**: See if it's already been proposed
- **Explain the use case**: Why would this be useful?
- **Consider scope**: Does it fit the project's goals?

### Submitting Pull Requests

1. **Fork the repository**
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Write tests**: Ensure your changes are tested
5. **Run tests locally**: `pytest`
6. **Run linter**: `ruff check . && ruff format .`
7. **Update documentation**: If you're changing behavior
8. **Commit with clear messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/)
9. **Push and create PR**: Include a clear description of changes

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

```bash
# Clone your fork
git clone https://github.com/your-username/falk.git
cd falk

# Create virtual environment and install dependencies
uv venv
uv sync --extra dev

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/falk --cov-report=html

# Run specific test file
pytest tests/test_agent.py

# Run with verbose output
pytest -v
```

### Running the Linter

```bash
# Check code
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### Running the Example

```bash
# Load sample data
uv run python examples/seed_data.py

# Start web UI
uv run uvicorn app.web:app --reload

# Or run Slack bot
uv run python app/slack.py
```

### Building Documentation

```bash
# Install docs dependencies
uv sync --extra docs

# Serve docs locally
uv run mkdocs serve --dev-addr=127.0.0.1:8001

# Build docs
uv run mkdocs build
```

## Project Structure

```
falk/
├── src/falk/          # Core library
│   ├── agent.py            # DataAgent class (BSL + DuckDB)
│   ├── pydantic_agent.py   # Pydantic AI agent + tools
│   ├── prompt.py           # System prompt generation
│   ├── cli.py              # CLI commands
│   ├── tools/              # Agent tools (query, export, charts)
│   └── evals/              # Evaluation framework
├── app/                     # Entry points (Slack, web, MCP)
├── config/                  # Example configuration (YAML)
├── examples/                # Sample data, evals, agent skills
├── docs/                    # Documentation (MkDocs)
└── tests/                   # Test suite
```

## Coding Standards

### Python Style

- **Follow PEP 8**: Use `ruff` for formatting
- **Type hints**: Use type annotations for function signatures
- **Docstrings**: Use Google-style docstrings for public APIs
- **Line length**: Max 100 characters (enforced by ruff)

### Example

```python
def query_metric(
    metric: str,
    group_by: list[str] | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Query a metric from the data warehouse.
    
    Args:
        metric: Metric name to query (e.g., "revenue", "trials")
        group_by: Optional list of dimensions to group by
        filters: Optional filter dictionary
    
    Returns:
        Dictionary containing rows and metadata
        
    Raises:
        ValueError: If metric is not found
    """
    ...
```

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add support for time-series queries
fix: resolve dimension lookup edge case
docs: update semantic models configuration guide
test: add tests for fuzzy entity matching
chore: update dependencies
```

## Areas We Need Help

### High Priority
- [ ] Industry-specific templates (e-commerce, media, finance)
- [ ] Integration tests for Slack bot
- [ ] Performance benchmarks
- [ ] Security audit (especially RLS policies)

### Medium Priority
- [ ] Additional export formats (Parquet, JSON)
- [ ] Chart customization options
- [ ] Caching layer for repeated queries
- [ ] dbt semantic layer integration

### Documentation
- [ ] Video tutorials
- [ ] More example projects
- [ ] Troubleshooting guide
- [ ] Production deployment best practices

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v0.1.0`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions will automatically publish to PyPI

## Questions?

- Check [Discussions](https://github.com/yourusername/falk/discussions)
- Open an [Issue](https://github.com/yourusername/falk/issues)
- Read the [Documentation](https://yourusername.github.io/falk/)

## License

By contributing to falk, you agree that your contributions will be licensed under the MIT License.

