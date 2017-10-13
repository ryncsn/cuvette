import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


def setup(loop):
    """
    Extract some settings from app
    Could be run in a different loop
    """
    class NoLogging(logging.Filter):
        def filter(self, record):
            return True

    # Suppress logging for now
    logging.getLogger("apscheduler").setLevel(logging.ERROR)
    logging.getLogger("apscheduler").addFilter(NoLogging())

    scheduler = AsyncIOScheduler()

    scheduler.configure({
        'event_loop': loop,
    })

    scheduler.start()

    return scheduler
