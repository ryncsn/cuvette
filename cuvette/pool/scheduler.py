import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


def setup(loop):
    class NoLogging(logging.Filter):
        def filter(self, record):
            return True

    # Suppress logging for now
    logging.getLogger("apscheduler").setLevel(logging.ERROR)
    logging.getLogger("apscheduler").addFilter(NoLogging())

    scheduler.configure({
        'event_loop': loop,
    })
    scheduler.start()
