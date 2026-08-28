# Contributing to DeepBl4nder

Thank you for your interest in contributing to DeepBl4nder! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

- Check existing issues to avoid duplicates
- Open an issue with a clear title and description
- Include steps to reproduce, expected behavior, and actual behavior
- Mention your OS, Python version, and Blender version if relevant

### Suggesting Features

- Open an issue with the `enhancement` label
- Describe the use case and how it fits the project vision
- Check the roadmaps in `docs/roadmaps/` for alignment with project goals

### Submitting Code

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/my-feature
   ```
3. Make your changes following the code conventions below
4. Run quality checks:
   ```bash
   ruff check DeepBl4nder tests
   mypy DeepBl4nder
   pytest
   ```
5. Commit with a clear message
6. Open a Pull Request against `main`

## Code Conventions

### Python

- Python 3.12+
- Use `from __future__ import annotations` at the top of every module
- Type annotations are required on all public functions
- Follow PEP 8 (enforced by ruff)
- Maximum line length: 120 characters

### NOOA / Domain Separation

- Agents live in `DeepBl4nder/agents/` and interact with NOOA
- Domain objects live in `DeepBl4nder/domain/` and are pure Python (no NOOA imports)
- Skills live in `DeepBl4nder/skills/` with a `SKILL.md` file per directory

### Commit Messages

- Use present tense ("add feature" not "added feature")
- Keep the first line under 72 characters
- Reference issues when applicable: "fix #42"

## Development Setup

```bash
# Clone the repo
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check DeepBl4nder tests

# Type check
mypy DeepBl4nder
```

## Questions?

Open an issue with the `question` label or start a discussion in the repository.
