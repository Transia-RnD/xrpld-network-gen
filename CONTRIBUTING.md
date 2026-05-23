# Contributing

## Setup

```bash
git clone https://github.com/Transia-RnD/xrpld-lab
cd xrpld-lab
poetry install
```

## Development

TDD workflow: write tests first, then implement.

```bash
# Run all tests
poetry run pytest tests/ -v

# Run a specific test file
poetry run pytest tests/unit/test_config_builder.py -v

# Run with coverage
poetry run pytest tests/ --cov=xrpld_lab
```

## Project structure

Source code lives in `xrpld_lab/`. Tests live in `tests/unit/`. Each module has a corresponding test file.

## Publishing

1. Bump version in `pyproject.toml`
2. Build: `poetry build`
3. Publish: `poetry publish`

Requires a PyPI API token configured via `poetry config pypi-token.pypi <token>`.
