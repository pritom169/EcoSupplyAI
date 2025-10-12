# Contributing to EcoSupplyAI

Thank you for your interest in contributing to EcoSupplyAI! This guide outlines the process for contributing to this project.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally: `git clone https://github.com/<your-username>/EcoSupplyAI.git`
3. **Create a feature branch** from `main`: `git checkout -b feature/your-feature-name`
4. **Install dependencies**: `make dev-install`

## Development Workflow

### Setting Up Your Environment

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install all dependencies (including dev tools)
make dev-install

# Copy environment template
cp .env.example .env
```

### Code Style

We use **Ruff** for linting and formatting. All code must pass these checks before merging.

```bash
# Run linter
make lint

# Auto-format code
make format

# Run type checking
make type-check
```

### Running Tests

```bash
# Run unit tests
make test

# Run tests with coverage
make test-cov
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. They are installed via `make dev-install`. To run them manually:

```bash
pre-commit run --all-files
```

## Submitting Changes

1. **Write tests** for any new functionality
2. **Run the full test suite** before submitting: `make test`
3. **Run linting and formatting**: `make lint` and `make format`
4. **Run evaluations** if your change touches AI behavior: `make eval-run`
5. **Commit** with a clear, descriptive message following [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `refactor:` for code refactoring
   - `test:` for adding or updating tests
   - `ci:` for CI/CD changes
6. **Push** your branch and open a **Pull Request** against `main`

## Pull Request Guidelines

- Provide a clear description of the changes and motivation
- Reference any related issues
- Ensure all CI checks pass
- Request review from at least one maintainer
- Keep PRs focused — one feature or fix per PR

## Reporting Bugs

Open an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs. actual behavior
- Environment details (OS, Python version, etc.)

## Code of Conduct

Please review our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing. We are committed to providing a welcoming and inclusive experience for everyone.

## Questions?

If you have questions about contributing, please open a Discussion on GitHub.
