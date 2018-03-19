"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging
import asyncio
import datetime
from dateutil.parser import parse

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
        self.reserve_duration = self.query['reserve-duration']

    async def on_start(self):
        for machine in self.machines:
            await machine.set({
                'reserve-duration': self.reserve_duration,
                'reserve-whilteboard': self.query['reserve-whiteboard']
            })

    async def on_done(self):
        for machine in self.machines:
            await perform_check(machine)
            await machine.set('status', 'ready')

    async def routine(self):
        for machine in self.machines:
            await machine.set({
                'status': 'reserved',
                'meta.reserve-start_time': datetime.datetime.now().isoformat()
            })
        try:
            await asyncio.sleep(self.reserve_duration)
        except asyncio.CancelledError as error:
            logger.exception(error)

    async def resume_routine(self):
        for machine in self.machines:
            await machine.set('status', 'reserved')
        try:
            start_time = machine['meta']['reserve-start_time']
            if isinstance(start_time, str):
                start_time = parse(start_time)
            seconds = (datetime.datetime.now() - start_time).seconds
            seconds = self.reserve_duration - seconds
            if seconds > 0:
                await asyncio.sleep(seconds)
        except asyncio.CancelledError as error:
            logger.exception(error)
