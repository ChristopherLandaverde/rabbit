"""Global pytest configuration and fixtures."""

import pytest
import sys
import os
from pathlib import Path
from redis import Redis

# Add src to Python path for testing
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def _read_known_failures():
    """Read strict xfail node IDs and collection-ignore modules."""
    entries = {}
    ignored_modules = []
    known_failures_path = Path(__file__).parent / "tests" / "known_failures.txt"
    reason = "Known failure recorded in tests/known_failures.txt"

    for raw_line in known_failures_path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.lower().startswith("# reason:"):
                reason = line.split(":", 1)[1].strip()
            continue
        if line.startswith("module:"):
            ignored_modules.append(line.removeprefix("module:"))
        else:
            entries[line] = reason

    return entries, ignored_modules


_KNOWN_FAILURES, collect_ignore = _read_known_failures()


def _read_redis_required_tests():
    path = Path(__file__).parent / "tests" / "redis_required.txt"
    return {
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


_REDIS_REQUIRED_TESTS = _read_redis_required_tests()


def pytest_collection_modifyitems(items):
    """Mark only the baseline failures as strict xfails."""
    for item in items:
        if item.nodeid in _REDIS_REQUIRED_TESTS:
            item.add_marker(pytest.mark.needs_redis)
        reason = _KNOWN_FAILURES.get(item.nodeid)
        if reason:
            item.add_marker(pytest.mark.xfail(strict=True, reason=reason))


@pytest.fixture(scope="session")
def redis_available():
    """Probe the configured Redis endpoint once for this pytest session."""
    client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD") or None,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        return bool(client.ping())
    except Exception:
        return False
    finally:
        client.close()


@pytest.fixture(autouse=True)
def skip_tests_requiring_redis(request, redis_available):
    """Skip live-Redis tests when their configured endpoint is unavailable."""
    if request.node.get_closest_marker("needs_redis") and not redis_available:
        pytest.skip("needs Redis")


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "tests" / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before running tests."""
    # Set test environment variables
    import os
    os.environ["TESTING"] = "true"
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Cleanup after tests
    pass


# Configure pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "algorithm: Algorithm correctness tests")
    config.addinivalue_line("markers", "needs_redis: Requires a reachable Redis service")
