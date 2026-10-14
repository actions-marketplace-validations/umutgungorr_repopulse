# Contributing to RepoPulse

Thank you for your interest in contributing to **RepoPulse**! We welcome bug reports, algorithm improvements, performance optimizations, documentation enhancements, and pull requests.

---

## 🧭 Core Principles

1. **Zero External Dependencies**: Runtime code (`src/repopulse/`) MUST rely strictly on Python 3.9+ standard library modules (`sys`, `os`, `re`, `subprocess`, `math`, `dataclasses`, `pathlib`, `json`, `argparse`, `collections`, `itertools`). No third-party runtime dependencies are permitted (no GitPython, no Pandas, no Rich).
2. **Sub-20ms Cold Startup**: CLI startup time is critical for CI quality gates and local developer workflows. Avoid heavy top-level imports.
3. **Cross-Platform Git Parity**: Mining operations must run flawlessly on Linux, macOS, and Windows. All Git subprocess invocations must handle Windows CRLF line endings, UTF-8 character encoding with safe fallback, and path separators gracefully.
4. **Resilience Over Crashes**: Malformed Git logs, huge bulk commits, or binary files must be handled cleanly without crashing.

---

## 🛠️ Local Development Setup

We recommend using [`uv`](https://github.com/astral-sh/uv) or standard Python `venv`:

```bash
# Clone the repository
git clone https://github.com/umutgungorr/repopulse.git
cd repopulse

# Install in editable mode with development dependencies
uv pip install -e ".[dev]"
# Or with standard pip:
pip install -e ".[dev]"
```

---

## 🧪 Running the Test Suite

Our test suite uses `pytest`:

```bash
# Run tests with uv
uv run --with pytest --with pytest-cov pytest

# Or with activated virtual environment
pytest --cov=src/repopulse --cov-report=term-missing
```

Ensure all tests pass and coverage remains above 90% before submitting a PR.

---

## 🎨 Code Style and Formatting

We enforce strict formatting and linting rules using [`ruff`](https://github.com/astral-sh/ruff):

```bash
# Check code for lint errors
uv run --with ruff ruff check .

# Format code
uv run --with ruff ruff format .
```

---

## 📦 Pull Request Process

1. Fork the repo and create a new feature branch (`git checkout -b feat/my-new-feature`).
2. Add comprehensive unit tests in `tests/` covering both happy paths and edge cases (boundary values, malformed commit messages, empty repositories).
3. Ensure `ruff check .` and `pytest` both pass cleanly with 100% success rate.
4. Commit your changes with clear semantic messages (`feat: ...`, `fix: ...`, `docs: ...`).
5. Open a Pull Request on GitHub and provide a concise summary of the changes and motivation.
