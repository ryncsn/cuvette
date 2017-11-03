"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging

from cuvette.inspectors import perform_check
from cuvette.tasks import BaseTask

logger = logging.getLogger(__name__)


class ProvisionTask(BaseTask):
    """
    The helper task to provision a machine
    """
    TYPE = 'provision'
    PARAMETERS = {
        'provision-count': {
            'type': int,
            'op': [None],
            'default': lambda query: query.get('count', 1)
        },
        'provision-whiteboard': {
            'type': str,
            'op': [None],
            'default': lambda query: query.get('whiteboard', '')
        }
    }

    def __init__(self, machines, query, provisioner, *args, **kwargs):
        super(ProvisionTask, self).__init__(machines, query, *args, **kwargs)
        self.provisioner = provisioner

    async def routine(self):
        for machine in self.machines:
            machine['provisioner'] = self.provisioner.NAME
            machine['status'] = 'preparing'
            await machine.save()
        await self.provisioner.provision(self.machines, self.query)
        for machine in self.machines:
            await perform_check(machine)
            machine['status'] = 'ready'
            await machine.save()
