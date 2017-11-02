"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging
import asyncio

from cuvette.tasks import BaseTask
from cuvette.inspectors import perform_check

logger = logging.getLogger(__name__)


class ReserveTask(BaseTask):
    """
    The revervation task, wait for given time then the task is done
    """
    TYPE = 'reserve'
    PARAMETERS = {
        'reserve-duration': {
            'type': int,
            'op': [None],
            'default': lambda query: query.get('duration') or 86400,
            'description': "Duration time for reservation in seconds"
        },
        'reserve-count': {
            'type': int,
            'op': [None],
            'default': lambda query: query.get('count', 1)
        },
        'reserve-whiteboard': {
            'type': str,
            'op': [None],
            'default': lambda query: query.get('whiteboard', '')
        }
    }

    def __init__(self, machines, query, *args, **kwargs):
        super(ReserveTask, self).__init__(machines, query, *args, **kwargs)
        self.reserve_duration = query['reserve-duration']
        self.meta['reserve-duration'] = self.reserve_duration
        self.meta['reserve-whiteboard'] = query['reserve-whiteboard']

    async def on_done(self):
        for machine in self.machines:
            await perform_check(machine)
            machine['status'] = 'ready'
        await super(ReserveTask, self).on_success()

    async def routine(self):
        for machine in self.machines:
            machine['status'] = 'reserved'
            await machine.save()
        try:
            await asyncio.sleep(self.reserve_duration)
        except Exception as error:
            # Most likely cancelled
            logger.exception(error)
