"""
SatQuery AI — PyTest Global Fixtures
Ensures test database tables and isolated test environments are initialized.
"""
import os
import pytest
from backend.app.db.session import ensure_db_tables, get_async_engine

# Force test environment
os.environ["SATQUERY_ENV"] = "test"


@pytest.fixture(autouse=True, scope="function")
async def setup_test_database():
    """Initializes schema before tests and cleans up where appropriate."""
    engine = get_async_engine()
    if "sqlite" in str(engine.url):
        await ensure_db_tables()
    yield
