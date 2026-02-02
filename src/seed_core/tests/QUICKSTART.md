# Quick Start Guide - Seed Core Tests

## Installation

```bash
# Navigate to seed_core directory
cd C:/seed/seed_core

# Install test dependencies
pip install -r requirements-test.txt

# Install seed_core in development mode (if not already installed)
pip install -e .
```

## Run Tests

### Basic Test Run
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with very verbose output (show each test)
pytest -vv
```

### Coverage Reports
```bash
# Run with coverage (terminal output)
pytest --cov=seed_core

# Run with coverage and show missing lines
pytest --cov=seed_core --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=seed_core --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Specific Tests
```bash
# Run specific file
pytest tests/test_pulse.py
pytest tests/test_status.py
pytest tests/test_reality.py
pytest tests/test_cli.py

# Run specific class
pytest tests/test_pulse.py::TestPulseResult

# Run specific test
pytest tests/test_pulse.py::TestPulseResult::test_pulse_result_creation
```

### Useful Options
```bash
# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Run last failed tests
pytest --lf

# Show print statements
pytest -s

# Quiet mode (less output)
pytest -q

# Show test durations
pytest --durations=10
```

## Expected Output

```
$ pytest -v
======================== test session starts ========================
platform win32 -- Python 3.x.x, pytest-7.x.x
collected 71 items

tests/test_cli.py::TestCLICommands::test_pulse_command_basic PASSED
tests/test_cli.py::TestCLICommands::test_pulse_command_with_reality PASSED
...
tests/test_pulse.py::TestPulseResult::test_pulse_result_creation PASSED
tests/test_pulse.py::TestHashVerification::test_compute_file_hash PASSED
...
tests/test_reality.py::TestRealityLoading::test_load_reality_from_path PASSED
...
tests/test_status.py::TestSeedStatus::test_seed_status_all_green PASSED
...

======================== 71 passed in 2.5s =========================
```

## Coverage Report

```
$ pytest --cov=seed_core --cov-report=term-missing

----------- coverage: platform win32, python 3.x.x -----------
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
seed_core/__init__.py      15      0   100%
seed_core/pulse.py         45      5    89%   78-82
seed_core/status.py        38      3    92%   65-67
seed_core/reality.py       52      6    88%   89-95
seed_core/cli.py           67      8    88%   45-48, 78-81
-----------------------------------------------------
TOTAL                     217     22    90%

======================== 71 passed in 3.2s =========================
```

## Troubleshooting

### ModuleNotFoundError: No module named 'seed_core'
**Solution**: Install seed_core in development mode:
```bash
pip install -e .
```

### ImportError: No module named 'pytest'
**Solution**: Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Tests fail with FileNotFoundError
**Solution**: Tests use fixtures that create temporary directories. This should work automatically. If issues persist, check that pytest can write to temp directories.

### Coverage percentage is 0%
**Solution**: Ensure seed_core is installed:
```bash
pip install -e .
pytest --cov=seed_core
```

## Test Organization

```
tests/
├── conftest.py         # Shared fixtures (temp dirs, mock models)
├── test_pulse.py       # Pulse/heartbeat monitoring (71 tests)
├── test_status.py      # Status aggregation (15 tests)
├── test_reality.py     # Reality loading (18 tests)
└── test_cli.py         # CLI commands (24 tests)
```

## Common Workflows

### Development Workflow
```bash
# 1. Make code changes
vim seed_core/pulse.py

# 2. Run related tests
pytest tests/test_pulse.py -v

# 3. Check coverage
pytest tests/test_pulse.py --cov=seed_core.pulse --cov-report=term-missing

# 4. Run all tests before commit
pytest -v
```

### CI/CD Workflow
```bash
# Run with strict coverage requirement
pytest --cov=seed_core --cov-fail-under=80 --cov-report=xml

# Generate multiple report formats
pytest --cov=seed_core --cov-report=term --cov-report=xml --cov-report=html
```

### Debug Workflow
```bash
# Run with pdb debugger on failure
pytest --pdb

# Run with verbose failure output
pytest -vv --tb=long

# Show local variables on failure
pytest -l --tb=short
```

## Next Steps

1. ✓ Install dependencies: `pip install -r requirements-test.txt`
2. ✓ Run tests: `pytest -v`
3. ✓ Check coverage: `pytest --cov=seed_core --cov-report=html`
4. Implement actual modules (replace mocks)
5. Update tests as needed
6. Maintain 80%+ coverage

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Click Testing Documentation](https://click.palletsprojects.com/en/8.1.x/testing/)

## Getting Help

- Check `tests/README.md` for detailed documentation
- Review `tests/TEST_SUMMARY.md` for test coverage overview
- Look at fixture definitions in `conftest.py`
- Examine existing tests for examples
