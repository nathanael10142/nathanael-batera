"""
Firestore-backed initialization wrapper.
The original SQLAlchemy-based init_db was archived to
backend/legacy_sql_backup/app/models/ (and other legacy files).

This module provides an async function `init_db()` that will populate
Firestore using the existing `backend/seed_data.py` script.
"""
import asyncio
import sys
import os

# Ensure repository root is on path so we can import seed_data
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # backend/seed_data.py contains `seed_database` function adapted for Firestore
    from backend import seed_data as _seed_module
except Exception:
    try:
        # fallback import if run from repo root differently
        import seed_data as _seed_module
    except Exception:
        _seed_module = None


async def init_db():
    """Populate Firestore with initial data using seed_data.seed_database().
    If seed_data is not available, raise RuntimeError.
    """
    if _seed_module is None or not hasattr(_seed_module, 'seed_database'):
        raise RuntimeError('Seed module not available. Use backend/seed_data.py to populate Firestore.')

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    await _seed_module.seed_database()


# Provide a synchronous entrypoint for convenience when called as a script
if __name__ == '__main__':
    asyncio.run(init_db())