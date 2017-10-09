"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging
import typing

from cuvette.pool.machine import Machine

from cuvette.provisioners.base import sanitize_query
from cuvette.inspectors import perform_check
from cuvette.tasks import BaseTask

logger = logging.getLogger(__name__)


class ProvisionTask(BaseTask):
    """
    The helper task to provision a machine
    """
    TYPE = 'provision'

    def __init__(self, machines: typing.List[Machine], provisioner, query, *args, **kwargs):
        super(ProvisionTask, self).__init__(machines, *args, **kwargs)
        self.provisioner = provisioner
        self.query = query

    async def routine(self):
        sanitized_query = sanitize_query(self.query, self.provisioner.accept)
        for machine in self.machines:
            machine['provisioner'] = self.provisioner.name
            machine['status'] = 'preparing'
            await machine.save()
        await self.provisioner.provision(self.machines, sanitized_query)
        for machine in self.machines:
            await perform_check(machine)
            machine['status'] = 'ready'
            await machine.save()
