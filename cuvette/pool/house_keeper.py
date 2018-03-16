import asyncio
import logging
from datetime import datetime
from cuvette.tasks.base import Tasks
from cuvette.tasks.teardown import TeardownTask
from cuvette.machine import Machine

logger = logging.getLogger(__name__)


class CleanExpiredMachine(object):
    """
    The worker function that keep scanning
    main pool to clean expired machines
    """

    INTERVAL = 60

    def __init__(self, db):
        self.db = db

    async def run(self):
        teardown_tasks = []
        for machine in await Machine.find_all(self.db, {
            'expire_time': {
                '$lte': datetime.now()
            }
        }):
            if any(task['type'] == 'teardown' for task in machine['tasks'].values()):
                continue  # TODO: use mongo query
            teardown_tasks.append(TeardownTask([machine], {}).run())
            logger.debug('Machine %s marked as teardown', machine)
        # Wait for INTERVAL seconds for tasks to finished, else change into async mode
        if teardown_tasks:
            finished, pending = await asyncio.wait(teardown_tasks, timeout=self.INTERVAL)


class CleanDeadMachine(object):
    """
    The worker function that keep scanning
    main pool to clean expired machines
    """

    INTERVAL = 60

    def __init__(self, db):
        self.db = db

    async def run(self):
        for machine in await Machine.find_all(self.db, {
            'tasks': {},
            'status': {
                '$ne': 'ready'
            }
        }):
            logger.debug('Deleting dead machine: %s', machine)
            machine.delete()
