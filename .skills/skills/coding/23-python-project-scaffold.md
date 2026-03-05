---
name: python-project-scaffold
description: "Generate complete Python project structure with pyproject.toml, src layout, testing configuration, ruff linting, type checking, pre-commit hooks, and documentation skeleton."
category: coding
difficulty: beginner
model_boost: "Weak models create inconsistent Python project structures with poor dependency management"
---

# Python Project Scaffold

## Purpose
This skill generates a production-ready Python project structure following modern best practices, including pyproject.toml-based dependency management, source layout (src/package_name), comprehensive testing configuration with pytest, automated linting with ruff, type checking with mypy, pre-commit hooks for code quality enforcement, and documentation skeleton. Output is a fully functional starter project that integrates seamlessly with CI/CD pipelines and development workflows.

## When to Use
- Starting new Python projects (web apps, libraries, CLI tools, data science)
- Migrating from setup.py to modern pyproject.toml configuration
- Establishing testing and code quality standards in existing projects
- Setting up development environment for team collaboration
- Implementing pre-commit hooks to enforce code standards automatically
- Creating library packages ready for PyPI distribution
- **Do NOT use when**: Building Python 2.7 code, or using conda as exclusive package manager

## Instructions

### Step 1: Design Project Structure and Directory Layout
Create a scalable foundation for Python projects:

**Library/Package Structure:**
```
my_package/
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── core.py
│       ├── utils.py
│       └── exceptions.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_core.py
│   └── test_utils.py
├── docs/
│   ├── conf.py
│   ├── index.rst
│   └── api.rst
├── .github/
│   └── workflows/
│       ├── test.yml
│       ├── lint.yml
│       └── publish.yml
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── .pre-commit-config.yaml
└── CONTRIBUTING.md
```

**Web Application Structure:**
```
my_app/
├── src/
│   └── my_app/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── v1.py
│       │   └── health.py
│       ├── models/
│       ├── schemas/
│       ├── services/
│       └── middleware/
├── tests/
│   ├── test_api/
│       ├── test_v1.py
│       └── test_health.py
│   ├── test_services/
│   └── conftest.py
├── pyproject.toml
├── docker-compose.yml
└── Dockerfile
```

### Step 2: Create Modern pyproject.toml Configuration
Replace setup.py with declarative package configuration:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
version = "0.1.0"
description = "A brief description of the package"
readme = "README.md"
license = { text = "MIT" }
authors = [
    { name = "Your Name", email = "you@example.com" }
]
requires-python = ">=3.9"
dependencies = [
    "requests>=2.31.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "mypy>=1.5.0",
    "ruff>=0.0.290",
    "black>=23.9.0",
    "pre-commit>=3.4.0",
]
docs = [
    "sphinx>=7.2.0",
    "sphinx-rtd-theme>=1.3.0",
    "myst-parser>=2.0.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/my-package"
Documentation = "https://my-package.readthedocs.io"
Repository = "https://github.com/yourusername/my-package.git"
"Bug Tracker" = "https://github.com/yourusername/my-package/issues"

[tool.setuptools]
package-dir = { "" = "src" }

[tool.setuptools.packages]
find = { where = ["src"] }

[tool.setuptools.package-data]
my_package = ["py.typed"]

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = "-v --cov=src/my_package --cov-report=term-missing --cov-report=html"
python_files = ["test_*.py", "*_test.py"]
asyncio_mode = "auto"

[tool.coverage.run]
source = ["src/my_package"]
branch = true
omit = [
    "*/tests/*",
    "*/site-packages/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "if t.TYPE_CHECKING:",
]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[tool.ruff]
line-length = 100
target-version = "py39"
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # Pyflakes
    "I",    # isort
    "C",    # flake8-comprehensions
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
    "ARG",  # flake8-unused-arguments
    "SIM",  # flake8-simplify
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.isort]
known-first-party = ["my_package"]
force-single-line = true
use-parentheses = true
ensure-newline-before-comments = true

[tool.black]
line-length = 100
target-version = ["py39"]
include = '\.pyi?$'
```

### Step 3: Configure Testing with pytest
Set up comprehensive testing infrastructure:

**conftest.py:**
```python
import os
import pytest
from pathlib import Path

@pytest.fixture
def test_data_dir():
    """Provides path to test data directory."""
    return Path(__file__).parent / "data"

@pytest.fixture
def sample_config():
    """Provides sample configuration for tests."""
    return {
        "debug": True,
        "api_url": "http://localhost:8000",
        "timeout": 5,
    }

@pytest.fixture(autouse=True)
def reset_env_vars(monkeypatch):
    """Reset environment variables before each test."""
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
```

**test_example.py:**
```python
import pytest
from my_package.core import calculate_total

class TestCalculateTotal:
    """Test suite for calculate_total function."""

    def test_positive_numbers(self):
        """Test with positive integers."""
        result = calculate_total([1, 2, 3])
        assert result == 6

    def test_empty_list(self):
        """Test with empty list."""
        result = calculate_total([])
        assert result == 0

    @pytest.mark.parametrize("input_val,expected", [
        ([1], 1),
        ([1, 1], 2),
        ([10, 20, 30], 60),
    ])
    def test_parametrized(self, input_val, expected):
        """Test with parametrized inputs."""
        assert calculate_total(input_val) == expected

    def test_invalid_input(self):
        """Test error handling."""
        with pytest.raises(TypeError):
            calculate_total("not a list")
```

### Step 4: Set Up Code Quality Tools
Configure linting, formatting, and type checking:

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.5
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
        args: [--strict]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, src/]
```

**Makefile (optional convenience):**
```makefile
.PHONY: install dev-install test lint format type-check security clean

install:
	pip install -e .

dev-install:
	pip install -e ".[dev,docs]"

test:
	pytest

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

type-check:
	mypy src/

security:
	bandit -r src/

clean:
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov dist build *.egg-info
```

### Step 5: Create Documentation Skeleton
Set up Sphinx for API documentation:

**docs/conf.py:**
```python
project = "My Package"
copyright = "2024, Your Name"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "myst_parser",
]
html_theme = "sphinx_rtd_theme"
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
master_doc = "index"
```

**docs/index.rst:**
```rst
My Package Documentation
========================

.. toctree::
   :maxdepth: 2

   api

.. automodule:: my_package
   :members:
   :undoc-members:
   :show-inheritance:
```

### Step 6: Configure Development Environment
Create helper scripts and environment files:

**.gitignore:**
```
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Type checking
.mypy_cache/
.dmypy.json
dmypy.json

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local
venv/
env/
```

**.python-version:**
```
3.11.0
```

### Step 7: Add CI/CD Integration
Create GitHub Actions workflows:

**.github/workflows/test.yml:**
```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip

      - run: pip install -e ".[dev]"
      - run: pytest
      - run: mypy src/
      - run: ruff check src/
```

## Output Template

```toml
# pyproject.toml
[project]
name = "{{package_name}}"
version = "{{version}}"
description = "{{description}}"
requires-python = "{{python_version}}"
dependencies = {{dependencies}}

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.mypy]
python_version = "{{python_version}}"

[tool.ruff]
line-length = {{line_length}}
```

```
Directory Structure
-------------------
{{package_name}}/
├── src/{{package_name}}/
│   ├── __init__.py
│   └── {{core_modules}}
├── tests/
│   └── {{test_files}}
├── docs/
├── pyproject.toml
└── .pre-commit-config.yaml
```

## Quality Gates
- [ ] Project uses src/ layout for packages (not flat structure)
- [ ] pyproject.toml contains all metadata, dependencies, and tool configuration
- [ ] pytest configured with coverage reporting and proper test discovery
- [ ] mypy configured with strict mode enabled
- [ ] ruff configured for linting and formatting
- [ ] .pre-commit-config.yaml includes trailing whitespace, mypy, ruff, and security checks
- [ ] GitHub Actions workflow tests against minimum and latest Python versions
- [ ] Documentation skeleton created with Sphinx or equivalent
- [ ] All configuration properly documented with comments explaining choices

## Examples

### Good Output (excerpt)
```toml
[project]
name = "data-processor"
version = "0.2.1"
requires-python = ">=3.9"
dependencies = ["pydantic>=2.0", "pandas>=2.0"]

[project.optional-dependencies]
dev = ["pytest>=7.4", "mypy>=1.5", "ruff>=0.1"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src/data_processor --cov-report=html"

[tool.mypy]
disallow_untyped_defs = true
strict_equality = true
```

### Bad Output (what to avoid)
```toml
[project]
name = "data-processor"
# Missing version, requires-python, classifiers
dependencies = ["pydantic", "pandas"]  # No version pins

# Missing tool configuration sections
# pyproject.toml file is incomplete
```

## Common Mistakes

1. **Using Flat Layout Instead of src/**: Mixing source code and tests in single directory makes packaging confusing. Import paths differ between editable install and published package. Solution: Always use src/package_name layout.

2. **Mixing setup.py and pyproject.toml**: Having both creates confusion about which takes precedence and complicates CI/CD. Solution: Migrate fully to pyproject.toml.

3. **No Version Pinning in Dependencies**: `requests` becomes `requests>=2.0` means requests 3.0 (released next year with breaking changes) automatically installs. App breaks without code changes. Solution: Pin major versions: `requests>=2.31.0,<3.0.0`.

4. **pytest Configured in setup.cfg Instead of pyproject.toml**: Keeping scattered configuration across files makes maintenance difficult. Solution: Consolidate everything in pyproject.toml under [tool.pytest.ini_options].

5. **Not Running Type Checking in CI**: mypy passes locally but fails in CI against newer type stubs. Breaks production deployment. Solution: Include `mypy src/` in CI pipeline.

6. **Skipping Pre-commit Hooks in Development**: Developers push code that fails linting/typing. CI rejects it; developer rebases and pushes again. Wastes time. Solution: Enforce pre-commit hooks locally: `pre-commit install`.

## Anti-Patterns

1. **Everything in one huge __init__.py**: Making the entire package importable from root pollutes namespace. Creates circular imports and tight coupling. Use submodules instead.

2. **Test Files in src/**: Distributing test code with package bloats installations. Test discovery becomes confused. Keep tests in separate tests/ directory.

3. **Hard-coded Configuration in Code**: Database URLs, API endpoints, secret keys scattered throughout codebase. Can't change environment without code changes. Use environment variables and .env files.

4. **Ignoring Python Version Compatibility**: Writing f-strings everywhere, then discovering users are on Python 3.8. Solution: `requires-python = ">=3.9"` forces specification.

5. **No Type Hints**: Code lacks type information; IDE can't autocomplete; future maintenance is painful. Solution: Enable strict mypy and require type hints for all functions.

6. **Tests That Import Installed Package**: Tests do `import my_package` instead of importing from src/. Means uninstalled code is never tested. Solution: Tests must import from src/ or editable install, never from site-packages.
