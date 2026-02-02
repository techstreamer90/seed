# Seed Core Test Suite

Comprehensive test suite for the seed-core package.

## Test Structure

```
tests/
├── conftest.py           # Shared pytest fixtures
├── test_pulse.py         # Pulse/heartbeat monitoring tests
├── test_status.py        # Status aggregation tests
├── test_reality.py       # Reality loading and validation tests
└── test_cli.py           # CLI command tests
```

## Test Files

### conftest.py
Provides shared fixtures for all tests:
- `temp_dir`: Temporary directory for test files
- `mock_model_path`: Mock BAM model file
- `mock_reality_dir`: Mock reality directory structure
- `mock_seed_model`: Mock seed meta-model
- `mock_pulse_data`: Mock pulse check data
- `mock_status_data`: Mock status aggregation data
- `create_model_file`: Factory for creating custom model files

### test_pulse.py
Tests for pulse/heartbeat monitoring functionality:
- **TestPulseResult**: PulseResult dataclass creation and validation
- **TestGetRealities**: Extracting realities from seed model
- **TestCheckReality**: Reality verification and status checking
- **TestHashVerification**: SHA-256 hash computation and verification
- **TestPulseAll**: Aggregation of pulse results across realities

Coverage:
- PulseResult dataclass with error handling
- Model parsing for reality nodes
- Hash verification (match/mismatch detection)
- File existence validation
- Status aggregation (green/yellow/red)

### test_status.py
Tests for status aggregation and reporting:
- **TestRealityStatus**: RealityStatus dataclass creation
- **TestSeedStatus**: SeedStatus aggregation logic
- **TestStatusRules**: Status determination rules (green/yellow/red)
- **TestFormatSummary**: Summary formatting (text and JSON)

Coverage:
- Status dataclass validation
- Aggregation of multiple reality statuses
- Priority rules (red > yellow > green)
- Text and JSON output formatting
- Empty state handling

### test_reality.py
Tests for reality loading and validation:
- **TestRealityLoading**: Loading realities from filesystem
- **TestModelParsing**: Parsing BAM model files
- **TestSourcePathResolution**: Resolving source file paths
- **TestRealityValidation**: Validating reality structure

Coverage:
- Reality loading from paths
- Model JSON parsing and validation
- Hierarchical model structures
- Node filtering by type
- Path resolution (absolute/relative)
- Schema validation

### test_cli.py
Tests for CLI commands using click.testing.CliRunner:
- **TestCLICommands**: Basic command execution
- **TestCLIErrorCases**: Error handling and edge cases
- **TestCLIOutputFormats**: Output formatting (JSON, text, verbose)
- **TestCLIWithFixtures**: Integration with pytest fixtures
- **TestCLIIntegration**: Full workflow integration tests

Coverage:
- CLI command invocation
- Argument parsing
- --json flag for JSON output
- Error cases (missing args, not found, invalid input)
- Help text generation
- Verbose/quiet modes

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_pulse.py
pytest tests/test_status.py
pytest tests/test_reality.py
pytest tests/test_cli.py
```

### Run specific test class
```bash
pytest tests/test_pulse.py::TestPulseResult
pytest tests/test_status.py::TestSeedStatus
```

### Run specific test
```bash
pytest tests/test_pulse.py::TestPulseResult::test_pulse_result_creation
```

### Run with coverage
```bash
pytest --cov=seed_core --cov-report=term-missing
```

### Run with coverage HTML report
```bash
pytest --cov=seed_core --cov-report=html
# View in browser: htmlcov/index.html
```

### Run with verbose output
```bash
pytest -v
```

### Run only fast tests (exclude slow tests)
```bash
pytest -m "not slow"
```

## Test Markers

Tests can be marked with custom markers:
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow-running tests

## Parametrized Tests

Many tests use `@pytest.mark.parametrize` for testing multiple scenarios:

```python
@pytest.mark.parametrize("status,verified,expected_valid", [
    ("green", True, True),
    ("yellow", True, False),
    ("red", False, False),
])
def test_reality_status_validation(self, status, verified, expected_valid):
    # Test logic here
```

## Coverage Goals

- **Target**: 80% code coverage minimum
- Configured in `pytest.ini` with `--cov-fail-under=80`
- Focus on critical paths and error handling

## Fixtures

### Using Fixtures

```python
def test_with_temp_dir(temp_dir: Path):
    """Test using temporary directory."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()

def test_with_mock_model(mock_model_path: Path):
    """Test using mock model."""
    import json
    data = json.loads(mock_model_path.read_text())
    assert data["type"] == "BAM"
```

### Factory Fixtures

```python
def test_custom_model(create_model_file):
    """Test with custom model data."""
    model_path = create_model_file({
        "id": "custom",
        "type": "BAM",
        "nodes": []
    })
    assert model_path.exists()
```

## Writing New Tests

### Test Naming Convention
- Test files: `test_<module>.py`
- Test classes: `Test<Feature>`
- Test functions: `test_<behavior>`

### Example Test Structure

```python
class TestFeature:
    """Test suite for Feature."""

    def test_basic_functionality(self):
        """Test basic feature works."""
        # Arrange
        data = {"key": "value"}

        # Act
        result = process(data)

        # Assert
        assert result is not None
        assert result["key"] == "value"

    def test_error_handling(self):
        """Test feature handles errors."""
        with pytest.raises(ValueError):
            process(None)

    @pytest.mark.parametrize("input,expected", [
        ("a", "A"),
        ("b", "B"),
    ])
    def test_multiple_cases(self, input, expected):
        """Test multiple input cases."""
        assert transform(input) == expected
```

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements-test.txt
    pytest --cov=seed_core --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Import Errors
If you get import errors, ensure seed_core is installed:
```bash
pip install -e .
```

### Fixture Not Found
Ensure `conftest.py` is in the tests directory and properly imported.

### Coverage Too Low
Run with `--cov-report=term-missing` to see which lines aren't covered:
```bash
pytest --cov=seed_core --cov-report=term-missing
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Clear Names**: Test names should describe behavior
3. **Arrange-Act-Assert**: Follow AAA pattern
4. **Fixtures**: Use fixtures for common setup
5. **Parametrize**: Use parametrize for multiple similar tests
6. **Coverage**: Aim for high coverage on critical paths
7. **Fast Tests**: Keep tests fast, mark slow tests appropriately
8. **Error Cases**: Test both success and failure paths

## Mock Implementation Note

The tests in this suite include mock implementations of the functions being tested. This is intentional to:
1. Document expected behavior
2. Enable tests to run before actual implementation
3. Serve as specification for the real implementation

When actual implementations are complete, replace the mock functions with imports from the real modules.
