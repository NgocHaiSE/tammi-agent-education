# Test Suite for Tammi Agent medical

Comprehensive test suite with organized structure for unit, integration, E2E, and external tests.

## Directory Structure

```
tests/
├── unit/                    # Fast unit tests with mocked dependencies
├── integration/             # Integration tests
│   ├── grpc/                # gRPC integration tests
│   ├── http/                # HTTP/SSE integration tests
│   ├── graph/               # Graph builder tests
│   └── llm/                 # LLM service tests
├── e2e/                     # End-to-end tests with running servers
├── external/                # Tests requiring real external APIs
├── manual/                  # Manual/debug scripts (not run in CI)
├── fixtures/                # Shared test data and fixtures
├── helpers/                 # Test utilities and helpers
├── ci/                      # CI-specific scripts
├── conftest.py              # Pytest configuration and fixtures
├── test_http_request.json   # HTTP test request examples
└── test_http_stream.json    # HTTP streaming test examples
```

## Running Tests

### Quick Start

```bash
# Run all unit tests (fast, < 2 minutes)
pytest tests/unit/ -v

# Run all integration tests
pytest tests/integration/ -v

# Run E2E tests (requires running servers at localhost:8000 and localhost:50051)
pytest tests/e2e/ -v

# Run specific test category
pytest tests/integration/test_grpc/ -v
```

### Using Markers

```bash
# Run only unit tests
pytest -m "unit" -v

# Run tests excluding slow/manual tests
pytest -m "not slow and not manual" -v

# Run tests that require gRPC server
pytest -m "requires_grpc_server" -v

# Run smoke tests only
pytest -m "smoke" -v
```

### Coverage

```bash
# Run with coverage report
pytest tests/unit/ --cov=agent --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # On macOS
start htmlcov/index.html  # On Windows
```

### CI Scripts

```bash
# Run unit tests (CI mode)
python tests/ci/run_unit_tests.py

# Run integration tests (CI mode)
python tests/ci/run_integration_tests.py

# Check code quality
python tests/ci/check_code_quality.py
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Fast**: < 1 second per test
- **Isolated**: All dependencies mocked
- **No I/O**: No network, file system, or database access
- **Examples**:
  - `test_medical_service.py` - Service layer tests
  - `test_router_mapping.py` - Router logic tests
  - `test_graph_builder_refactored.py` - Graph builder tests

### Integration Tests (`tests/integration/`)
- **Medium speed**: 1-10 seconds per test
- **Partial integration**: Some real components, some mocked
- **Limited I/O**: May use real local services
- **Subdirectories**:
  - `grpc/` - gRPC protocol tests
  - `http/` - HTTP and SSE tests
  - `graph/` - Graph execution tests
  - `llm/` - LLM service tests

### E2E Tests (`tests/e2e/`)
- **Slow**: 10+ seconds per test
- **Full integration**: All components working together
- **Real services**: Requires running HTTP (port 8000) and gRPC (port 50051) servers
- **Examples**:
  - `test_both_modes.py` - Tests both HTTP and gRPC modes
  - `comprehensive_test.py` - Full system test
  - `final_complete_test.py` - Complete workflow test

### External Tests (`tests/external/`)
- **Variable speed**: Depends on API response time
- **Real APIs**: Uses actual external services
- **Requires credentials**: API keys needed
- **Examples**: External API integration tests

### Manual Tests (`tests/manual/`)
- **Not run in CI**: For debugging and manual verification
- **Development tools**: Quick checks and experiments
- **Examples**:
  - `quick_health_check.py` - Health check script
  - `debug_test.py` - Debug utilities

## Test Helpers and Fixtures

### Fixtures (`tests/fixtures/`)
- `request_fixtures.py` - Sample agent requests and responses

### Helpers (`tests/helpers/`)
- `test_utils.py` - Common test utilities
- `grpc_utils.py` - gRPC testing utilities

## Prerequisites for E2E Tests

Before running E2E tests, ensure servers are running:

```bash
# Terminal 1: Start HTTP server
python -m agent.entrypoint.http_server

# Terminal 2: Start gRPC server
python -m agent.entrypoint.grpc_server

# Terminal 3: Run E2E tests
pytest tests/e2e/ -v
```

Or use the background scripts:

```bash
# Start both servers in background
python scripts/run_medical_bg.py

# Run E2E tests
pytest tests/e2e/ -v
```

## Environment Variables

Tests use these environment variables (set in `conftest.py` for unit tests):

```bash
# Azure OpenAI (required for real LLM testing)
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
OPENAI_API_VERSION=2024-02-15-preview

# Server configuration (for E2E tests)
GRPC_HOST=localhost
GRPC_PORT=50051
HTTP_HOST=localhost
HTTP_PORT=8000
```

## CI/CD Integration

GitHub Actions workflow (`.github/workflows/ci.yml`) runs:

1. **On every push/PR**:
   - Fast unit tests
   - Code quality checks

2. **On manual trigger** (with test suite selection):
   - Fast: Unit tests only
   - Integration: Unit + Integration tests
   - E2E: Full E2E tests with servers
   - Full: All tests

3. **On PR with labels**:
   - `test:integration` - Runs integration tests
   - `test:e2e` - Runs E2E tests
   - `test:full` - Runs all tests

## Writing New Tests

### Unit Test Template

```python
# tests/unit/test_example.py
import pytest
from unittest.mock import MagicMock
from tests.helpers.test_utils import create_mock_llm, clear_graph_cache

@pytest.mark.unit
def test_example_function(monkeypatch):
    """Test example function with mocked dependencies."""
    # Setup mocks
    mock_llm = create_mock_llm("Mocked response")
    monkeypatch.setattr('agent.llm_service.llm_config_service.create_medical_llm_client', 
                       lambda **kwargs: mock_llm)
    clear_graph_cache()
    
    # Test logic
    result = some_function()
    
    # Assertions
    assert result is not None
```

### Integration Test Template

```python
# tests/integration/test_grpc/test_example.py
import pytest
from tests.helpers.grpc_utils import GrpcServerManager, create_test_agent_request

@pytest.mark.integration
@pytest.mark.requires_grpc_server
@pytest.mark.asyncio
async def test_grpc_endpoint():
    """Test gRPC endpoint."""
    async with GrpcServerManager() as server:
        # Create request
        request = create_test_agent_request("Test message")
        
        # Send and verify
        # ... test logic ...
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `PYTHONPATH` includes project root
   ```bash
   export PYTHONPATH=$PWD  # Linux/Mac
   set PYTHONPATH=%CD%     # Windows
   ```

2. **Missing dependencies**: Install test requirements
   ```bash
   pip install -r requirements-test.txt
   ```

3. **E2E tests fail**: Ensure servers are running on correct ports
   ```bash
   # Check if servers are running
   curl http://localhost:8000/management/healthz
   grpcurl -plaintext localhost:50051 list
   ```

4. **Graph cache issues**: Clear cache between test runs
   ```python
   from agent.graph import builder
   builder._get_cached_graph.cache_clear()
   ```

## Best Practices

1. **Keep unit tests fast**: < 1 second each
2. **Mock external dependencies**: LLMs, APIs, databases
3. **Use fixtures**: Share common setup code
4. **Mark tests appropriately**: Use pytest markers
5. **Clean up resources**: Use context managers and teardown
6. **Test one thing**: Each test should verify one behavior
7. **Descriptive names**: Test names should describe what they test
8. **Document edge cases**: Add comments for complex scenarios

## Contributing

When adding new tests:

1. Place in appropriate directory (unit/integration/e2e/external/manual)
2. Add appropriate pytest markers
3. Follow naming convention: `test_*.py`
4. Update this README if adding new patterns
5. Ensure tests pass before committing

## License

Same as main project.
