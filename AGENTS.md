# OpenHands Testing Guide

## Setup
```bash
# Install dependencies
pipx install poetry
poetry install --with dev,test,runtime,evaluation
make build

# Create LLM config for integration tests
echo "[llm.eval]" > config.toml
echo "model = \"gpt-4o-mini\"" >> config.toml
echo "api_key = \"your-api-key\"" >> config.toml
echo "temperature = 0.0" >> config.toml
```

## Integration Tests
Tests agent performance on tasks in `evaluation/integration_tests/tests/`.

**Available:** t01_fix_simple_typo, t02_add_bash_hello, t03_jupyter_write_file, t04_git_staging, t05_simple_browsing, t06_github_pr_browsing, t07_interactive_commands

```bash
# Run all integration tests
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 5 1 '' 'test-run'

# Run specific test
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 5 1 "t01_fix_simple_typo" "test-run"

# Run multiple tests
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 5 1 "t01_fix_simple_typo,t02_add_bash_hello" "test-run"
```

## Runtime Tests
Environment functionality tests in `tests/runtime/`.

```bash
# Run all runtime tests
poetry run pytest -v tests/runtime/

# Run specific test
poetry run pytest -v tests/runtime/test_bash.py

# With different runtime
TEST_RUNTIME=cli poetry run pytest -v tests/runtime/test_bash.py
```

## Unit Tests
Component tests in `tests/unit/`.

```bash
# Run all unit tests
poetry run pytest --forked -n auto -v tests/unit/

# Run specific test
poetry run pytest -v tests/unit/test_api_connection_error_retry.py
```

## E2E Tests
Full application tests in `tests/e2e/`.

```bash
# Setup
poetry run playwright install chromium-headless-shell

# Start app
FRONTEND_PORT=12000 FRONTEND_HOST=0.0.0.0 BACKEND_HOST=0.0.0.0 make run &

# Run tests
cd tests/e2e
poetry run python -m pytest test_settings.py::test_github_token_configuration test_conversation.py::test_conversation_start -v --timeout=600
```

## Frontend Tests
```bash
make test-frontend
```

## Run All Tests
```bash
make build
poetry run pytest --forked -n auto -v tests/unit/
poetry run pytest -v tests/runtime/
export SANDBOX_FORCE_REBUILD_RUNTIME=true
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 5 1 '' 'local-test'
```