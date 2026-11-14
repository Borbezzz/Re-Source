"""Private Vercel queue consumer, discovered separately from the HTTP service."""
import os
import asyncio
import logging
import sys
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
sys.path.insert(0, str(Path(__file__).parent / "backend"))
from vercel.queue import subscribe
from recovery.runtime.jobs import topic, JobMessage

_tracing_started = False


@subscribe(topic=topic, consumer_group="recovery", max_concurrency=3, max_attempts=5, retry_after=timedelta(seconds=15))
async def consume(message: JobMessage) -> None:
    global _tracing_started
    from starlette.concurrency import run_in_threadpool
    from recovery.api.app import initialise_services
    services = await run_in_threadpool(initialise_services)
    if not _tracing_started:
        _tracing_started = True
        from recovery.runtime.tracing import init_tracing
        try:
            await asyncio.wait_for(asyncio.to_thread(init_tracing), timeout=3)
        except asyncio.TimeoutError:
            logging.getLogger(__name__).warning("Tracing setup exceeded 3s; job execution continues without waiting")
    await run_in_threadpool(services.jobs.execute, message.job_id)
