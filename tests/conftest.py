"""
Pytest configuration for Granger Hub tests.

This file configures pytest settings and fixtures for the entire test suite.
"""

import sys
import pytest
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add src to Python path
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


# Configure pytest settings
def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_ollama: mark test as requiring Ollama to be running"
    )
    config.addinivalue_line(
        "markers", "requires_arangodb: mark test as requiring ArangoDB"
    )


# Common fixtures
@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def fixtures_dir():
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


# Skip markers for optional dependencies
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add skip markers."""
    
    # Check if Ollama is available
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=1)
        ollama_available = response.status_code == 200
    except:
        ollama_available = False
    
    # Check if ArangoDB is available
    try:
        from arango import ArangoClient
        client = ArangoClient(hosts="http://localhost:8529")
        db = client.db("_system", username="root", password="")
        arangodb_available = True
    except:
        arangodb_available = False
    
    # Add skip markers
    skip_ollama = pytest.mark.skip(reason="Ollama not available")
    skip_arangodb = pytest.mark.skip(reason="ArangoDB not available")
    
    for item in items:
        if "requires_ollama" in item.keywords and not ollama_available:
            item.add_marker(skip_ollama)
        if "requires_arangodb" in item.keywords and not arangodb_available:
            item.add_marker(skip_arangodb)