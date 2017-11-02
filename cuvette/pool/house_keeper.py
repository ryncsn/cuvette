import asyncio
import logging
from datetime import datetime
from cuvette.tasks.teardown import TeardownTask
from cuvette.pool.machine import Machine

logger = logging.getLogger(__name__)


class Worker(object):
    """
    The worker function that keep scanning
    main pool to clean expired machines
    """

    HOUSE_KEEPING_INTERVAL = 5

    def __init__(self, db):
        self.db = db

    async def run(self):
        logger.debug('House keeeper started.')
        teardown_tasks = []
        for machine in await Machine.find_all(self.db, {
            'expire_time': {
                '$lte': datetime.now()
            }
        }):
            if any(task['type'] == 'teardown' for task in machine['tasks'].values()):
                continue  # TODO: use mongo query
            teardown_tasks.append(TeardownTask([machine], {}).run())
        # Wait for HOUSE_KEEPING_INTERVAL seconds for tasks to finished, else change into async mode
        if teardown_tasks:
            finished, pending = await asyncio.wait(teardown_tasks, timeout=self.HOUSE_KEEPING_INTERVAL)
