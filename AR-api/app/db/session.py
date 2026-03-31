"""
Backward-compatible module name.

Prefer importing from `app.db.database` going forward.
"""

from app.db import database as _database

async_engine = _database.async_engine
AsyncSessionLocal = _database.AsyncSessionLocal
get_db = _database.get_db
transaction_context = _database.transaction_context

__all__ = ["async_engine", "AsyncSessionLocal", "get_db", "transaction_context"]

