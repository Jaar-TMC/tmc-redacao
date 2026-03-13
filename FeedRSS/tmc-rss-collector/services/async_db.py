"""
Async wrapper for synchronous DatabaseService calls.

pymssql is blocking; this module wraps DB calls with asyncio.to_thread()
so async handlers don't block the Azure Functions event loop.

Thread safety: ConnectionPool.get_connection() returns a dedicated connection
per call, so concurrent threads never share a connection object.
"""

import asyncio
from typing import TypeVar, Callable

T = TypeVar('T')


async def run_db(func: Callable[..., T], *args, **kwargs) -> T:
    """Run a synchronous DB function in a thread pool.

    Usage:
        db = get_db()
        articles, total = await run_db(db.get_articles, page=1, limit=20)
    """
    return await asyncio.to_thread(func, *args, **kwargs)
