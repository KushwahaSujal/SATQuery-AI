"""
SatQuery AI — PyTest global fixtures and tier markers.

Tests are organised into three tiers by directory:

    tests/unit/         pure logic — no weights, no database, no network
    tests/integration/  database, API client, cross-module wiring
    tests/models/       needs real model weights (local or from HuggingFace)

The matching marker is applied automatically from the directory name, so
individual tests do not have to declare it:

    pytest -m unit              fast feedback loop while developing
    pytest -m "not models"      everything that runs without checkpoints
    pytest                      the lot
"""
import os

import pytest

from backend.app.db.session import ensure_db_tables, get_async_engine

# Force test environment: routes the DB to sqlite+aiosqlite (see db/session.py).
os.environ["SATQUERY_ENV"] = "test"

_TIER_BY_DIR = {"unit": "unit", "integration": "integration", "models": "models"}


def pytest_collection_modifyitems(config, items):
    """Tag every collected test with the marker for the directory it lives in."""
    for item in items:
        for part in item.nodeid.split("/"):
            tier = _TIER_BY_DIR.get(part)
            if tier:
                item.add_marker(getattr(pytest.mark, tier))
                break


@pytest.fixture(autouse=True, scope="function")
async def setup_test_database():
    """Initializes schema before tests and cleans up where appropriate."""
    engine = get_async_engine()
    if "sqlite" in str(engine.url):
        await ensure_db_tables()
    yield
