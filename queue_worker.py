"""Private Vercel queue consumer, discovered separately from the HTTP service."""
import os
import sys
from datetime import timedelta
from pathlib import Path
os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
sys.path.insert(0, str(Path(__file__).parent / "backend"))
from vercel.queue import subscribe
from recovery.runtime.jobs import topic, JobMessage


@subscribe(topic=topic, consumer_group="recovery", max_concurrency=3, max_attempts=5, retry_after=timedelta(seconds=15))
async def consume(message: JobMessage) -> None:
    from starlette.concurrency import run_in_threadpool
    from recovery.api.app import initialise_services
    services = await run_in_threadpool(initialise_services)
    await run_in_threadpool(services.jobs.execute, message.job_id)
