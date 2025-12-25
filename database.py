"""
Compatibility shim for legacy `database` imports.
This file provides a minimal API so the application can start on Render while
you migrate fully to Firebase/Firestore.

It does NOT provide a real SQL database. Any attempt to use the provided
session to execute SQL will raise a clear runtime error instructing to
migrate the logic to Firestore or re-enable a SQL DB.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

# Import Base from the application's models so scripts that expect Base will work
try:
    from app.models.base import Base
except Exception:
    # Fallback: create a very small placeholder if models are unavailable
    Base = None


class _DisabledSession:
    """Session stub that fails fast when used."""

    async def execute(self, *args, **kwargs):
        raise RuntimeError(
            "SQL access is disabled in this deployment. This project is configured to use Firebase/Firestore."
            " Convert database calls to Firestore or provide a real SQL database and a proper `database.py` implementation.")

    def scalars(self):
        raise RuntimeError("SQL access is disabled.")

    async def commit(self):
        raise RuntimeError("SQL access is disabled.")

    async def refresh(self, *args, **kwargs):
        raise RuntimeError("SQL access is disabled.")

    async def close(self):
        return

    # Sync helpers (for scripts that may call synchronously)
    def add(self, *args, **kwargs):
        raise RuntimeError("SQL access is disabled.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("SQL access is disabled.")


@asynccontextmanager
async def _dummy_async_session() -> AsyncIterator[_DisabledSession]:
    """Async context manager that yields a disabled session stub."""
    sess = _DisabledSession()
    try:
        yield sess
    finally:
        await sess.close()


# Exposed API expected by the codebase
async_session = _dummy_async_session

async def get_session():
    """FastAPI dependency compatible generator.

    Usage: db: AsyncSession = Depends(get_session)
    """
    async with async_session() as session:
        yield session
