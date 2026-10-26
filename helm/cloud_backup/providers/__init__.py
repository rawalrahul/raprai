"""Cloud backup provider implementations.

The providers' methods are coroutines, but they talk to Dropbox, Google Drive
and OneDrive with blocking urllib calls (an upload can take minutes). Call them
through ``off_loop`` so that work happens in a worker thread instead of
freezing RAPR's event loop, and with it the web UI, chat apps and every session.
"""

import asyncio


async def off_loop(method, *args):
    """Run ``await method(*args)`` on its own event loop in a worker thread."""
    return await asyncio.to_thread(asyncio.run, method(*args))
