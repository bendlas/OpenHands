# OpenHands Testing Guide

This document provides comprehensive guidance on running all types of tests in the OpenHands project.

## Prerequisites

Before running any tests, ensure you have the following dependencies installed:

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y tmux libgtk-3-0 libnotify4 libnss3 libxss1 libxtst6 xauth xvfb libgbm1 libasound2t64 netcat-openbsd

# Install Poetry (if not already installed)
pipx install poetry

# Install Python dependencies
poetry install --with dev,test,runtime,evaluation

# Install Node.js dependencies and build frontend
make build
```

## Test Categories

OpenHands has several categories of tests:

### 1. Integration Tests (Evaluation)

These are high-level tests that evaluate agent performance on specific tasks located in `evaluation/integration_tests/tests/`.

**Available Tests:**
- `t01_fix_simple_typo.py` - Tests basic file editing capabilities
- `t02_add_bash_hello.py` - Tests bash script creation
- `t03_jupyter_write_file.py` - Tests Jupyter notebook interactions
- `t04_git_staging.py` - Tests Git operations
- `t05_simple_browsing.py` - Tests web browsing capabilities
- `t06_github_pr_browsing.py` - Tests GitHub PR browsing
- `t07_interactive_commands.py` - Tests interactive command handling

**Setup Configuration:**
```bash
# Create config.toml for LLM configuration
echo "[llm.eval]" > config.toml
echo "model = \"gpt-4o-mini\"" >> config.toml
echo "api_key = \"your-api-key\"" >> config.toml
echo "temperature = 0.0" >> config.toml
```

**Run Individual Integration Tests:**
```bash
# Run a specific test using the script (recommended)
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 5 1 "t01_fix_simple_typo" "test-run"

# Run multiple specific tests
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 5 1 "t01_fix_simple_typo,t02_add_bash_hello" "test-run"

# Script parameters: [model_config] [git-version] [agent] [eval_limit] [max_iterations] [num_workers] [eval_ids] [eval_note]
```

**Run All Integration Tests:**
```bash
# Run all integration tests
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 10 1 '' 'all-tests'

# Run with limited iterations for faster testing
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 5 1 '' 'quick-test'
```

**Alternative method using Python script directly:**
```bash
# Note: The direct Python script has different arguments and is less commonly used
poetry run python evaluation/integration_tests/run_infer.py \
  --agent-cls CodeActAgent \
  --llm-config llm.eval \
  --max-iterations 5 \
  --task "Fix typos in bad.txt"
```

**Loop through individual tests manually:**
```bash
# Loop through all integration tests using the recommended script
for test_file in evaluation/integration_tests/tests/t*.py; do
  if [ -f "$test_file" ]; then
    test_name=$(basename "$test_file" .py)
    echo "Running test: $test_name"
    poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 5 1 "$test_name" "individual-test"
  fi
done
```

**Alternative Agent Tests:**
```bash
# Test with VisualBrowsingAgent (for browsing tests)
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD VisualBrowsingAgent '' 15 1 "t05_simple_browsing,t06_github_pr_browsing" 'visual-browsing-test'
```

**Script Parameter Explanation:**
The `run_infer.sh` script takes these parameters in order:
1. `model_config` - LLM config name from config.toml (e.g., "llm.eval")
2. `git_version` - Git commit/branch/tag (e.g., "HEAD")
3. `agent` - Agent class name (e.g., "CodeActAgent", "VisualBrowsingAgent")
4. `eval_limit` - Limit number of tests (empty string for no limit)
5. `max_iterations` - Maximum iterations per test (e.g., 5, 10, 15)
6. `num_workers` - Number of parallel workers (usually 1 for debugging)
7. `eval_ids` - Specific test IDs to run (empty for all, or comma-separated like "t01_fix_simple_typo,t02_add_bash_hello")
8. `eval_note` - Note to identify this test run

### 2. Runtime Tests

These tests verify runtime environment functionality located in `tests/runtime/`.

**Available Runtime Tests:**
- `test_bash.py` - Tests bash command execution
- `test_browsergym_envs.py` - Tests browser environment setup
- `test_browsing.py` - Tests browsing capabilities
- `test_docker_images.py` - Tests Docker image handling
- `test_env_vars.py` - Tests environment variable handling
- `test_glob_and_grep.py` - Tests file operations
- `test_ipython.py` - Tests IPython integration
- `test_llm_based_edit.py` - Tests LLM-based editing
- `test_microagent.py` - Tests microagent functionality
- `test_setup.py` - Tests runtime setup

**Run All Runtime Tests:**
```bash
poetry run pytest -v tests/runtime/
```

**Run Specific Runtime Tests:**
```bash
# Test bash functionality
poetry run pytest -v tests/runtime/test_bash.py

# Test browsing functionality
poetry run pytest -v tests/runtime/test_browsing.py

# Test with specific runtime (default is Docker)
TEST_RUNTIME=cli poetry run pytest -v tests/runtime/test_bash.py
```

**Runtime Environment Options:**
- `docker` (default) - Docker runtime
- `local` - Local runtime
- `cli` - CLI runtime
- `remote` - Remote runtime

### 3. Unit Tests

These are isolated component tests located in `tests/unit/`.

**Run All Unit Tests:**
```bash
poetry run pytest --forked -n auto -v tests/unit/
```

**Run Specific Unit Tests:**
```bash
# Test API connection handling
poetry run pytest -v tests/unit/test_api_connection_error_retry.py

# Test CLI functionality
poetry run pytest -v tests/unit/test_cli_*.py
```

### 4. End-to-End (E2E) Tests

These tests verify the complete application workflow located in `tests/e2e/`.

**Setup for E2E Tests:**
```bash
# Install Playwright
poetry run playwright install chromium-headless-shell

# Verify Playwright installation
poetry run python tests/e2e/check_playwright.py
```

**Start OpenHands for E2E Testing:**
```bash
# Start OpenHands server
FRONTEND_PORT=12000 FRONTEND_HOST=0.0.0.0 BACKEND_HOST=0.0.0.0 make run &

# Wait for server to start (check with curl or nc)
curl http://localhost:12000
```

**Run E2E Tests:**
```bash
cd tests/e2e
poetry run python -m pytest test_settings.py::test_github_token_configuration test_conversation.py::test_conversation_start -v --no-header --capture=no --timeout=600
```

**Available E2E Tests:**
- `test_settings.py` - Tests application settings
- `test_conversation.py` - Tests conversation functionality
- `test_local_runtime.py` - Tests local runtime integration

### 5. Frontend Tests

Frontend-specific tests for the React application.

**Run Frontend Tests:**
```bash
make test-frontend
# or
cd frontend && npm run test
```

## Automated Testing via GitHub Actions

The repository includes automated testing workflows:

### Integration Tests Workflow
- **File:** `.github/workflows/integration-runner.yml`
- **Trigger:** PR label `integration-test`, manual dispatch, or nightly schedule
- **Tests:** Runs integration tests with multiple LLM models (Haiku, DeepSeek)

### Python Tests Workflow
- **File:** `.github/workflows/py-tests.yml`
- **Trigger:** Push to main, PRs
- **Tests:** Unit tests and basic runtime tests

### E2E Tests Workflow
- **File:** `.github/workflows/e2e-tests.yml`
- **Trigger:** PR label `end-to-end` or manual dispatch
- **Tests:** Full end-to-end application tests

### Custom Copilot Setup Workflow
- **File:** `.github/workflows/copilot-setup-steps.yml`
- **Trigger:** Manual dispatch with test type selection
- **Tests:** Comprehensive test suite covering all categories

## Running All Tests Locally

To run the complete test suite locally:

```bash
# 1. Build the project
make build

# 2. Run unit tests
poetry run pytest --forked -n auto -v tests/unit/

# 3. Run runtime tests
poetry run pytest -v tests/runtime/

# 4. Set up integration test config
echo "[llm.eval]" > config.toml
echo "model = \"gpt-4o-mini\"" >> config.toml
echo "api_key = \"your-api-key\"" >> config.toml
echo "temperature = 0.0" >> config.toml

# 5. Run integration tests using the recommended script
export SANDBOX_FORCE_REBUILD_RUNTIME=true
poetry run ./evaluation/integration_tests/scripts/run_infer.sh llm.eval HEAD CodeActAgent '' 5 1 '' 'local-test'

# 6. Set up and run E2E tests
poetry run playwright install chromium-headless-shell
FRONTEND_PORT=12000 FRONTEND_HOST=0.0.0.0 BACKEND_HOST=0.0.0.0 make run &
# Wait for server to start, then:
cd tests/e2e
poetry run python -m pytest -v --timeout=600

# 7. Run frontend tests
make test-frontend
```

## Environment Variables

Key environment variables for testing:

- `TEST_RUNTIME` - Runtime type for runtime tests (docker, local, cli, remote)
- `LLM_MODEL` - Model to use for LLM-based tests
- `LLM_API_KEY` - API key for LLM services
- `LLM_BASE_URL` - Base URL for LLM API
- `FRONTEND_PORT` - Port for frontend server (default: 3001)
- `BACKEND_PORT` - Port for backend server (default: 3000)
- `TEST_IN_CI` - Set to 'True' when running in CI
- `SANDBOX_FORCE_REBUILD_RUNTIME` - Force rebuild of runtime containers

## Troubleshooting

### Common Issues

1. **Poetry not found**: Install poetry with `pipx install poetry`
2. **Docker not available**: Ensure Docker is installed and running
3. **Port conflicts**: Change FRONTEND_PORT/BACKEND_PORT if defaults are in use
4. **LLM API failures**: Verify API key and model availability
5. **Playwright issues**: Run `poetry run playwright install` to install browsers

### Debug Commands

```bash
# Check system dependencies
make check-dependencies

# View build logs
make build 2>&1 | tee build.log

# Check running processes
ps aux | grep -E "(openhands|npm|python)"

# Check port availability
netstat -tulpn | grep -E ":(3000|3001|12000)"
```

## CI/CD Integration

To trigger automated tests:

1. **Integration Tests**: Add `integration-test` label to your PR
2. **E2E Tests**: Add `end-to-end` label to your PR
3. **Manual Trigger**: Use GitHub Actions "workflow_dispatch" for any workflow

The copilot-setup-steps workflow can be manually triggered with different test types:
- `all` - Run all test categories
- `integration_tests` - Run only evaluation integration tests
- `runtime` - Run only runtime tests
- `e2e` - Run only end-to-end tests