"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging

from cuvette.inspectors import perform_check
from cuvette.tasks import BaseTask
from cuvette.utils.exceptions import ProvisionError
from cuvette.provisioners import find_by_name

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

    @classmethod
    async def resume(cls, uuid, query, machines):
        provisioner = find_by_name(machines[0]['provisioner'])
        return await super(ProvisionTask, cls).resume(uuid, query, machines, provisioner)

    async def on_start(self):
        await super(ProvisionTask, self).on_start()
        for machine in self.machines:
            await machine.set('provisioner', self.provisioner.NAME)

    async def routine(self):
        # TODO: Better pre parameters passthrough
        for machine in self.machines:
            for key, value in self.query.items():
                if isinstance(value, str):
                    machine[key] = value
            await machine.set('provisioner', self.provisioner.NAME)
            await machine.set('status', 'preparing')
        try:
            await self.provisioner.provision(self.machines, self.query)
        except (ProvisionError, RuntimeError) as error:
            for machine in self.machines:
                await machine.fail(error.message or 'Unknown failure')
        else:
            for machine in self.machines:
                await perform_check(machine)

    async def resume_routine(self):
        # TODO: Better pre parameters passthrough
        for machine in self.machines:
            for key, value in self.query.items():
                if isinstance(value, str):
                    machine[key] = value
            await machine.save()
            if machine['status'] != 'preparing':
                await machine.set('status', 'preparing')
        try:
            await self.provisioner.resume(self.machines, self.query)
        except (ProvisionError, RuntimeError) as error:
            for machine in self.machines:
                await machine.fail(error.message or 'Unknown failure')
        else:
            for machine in self.machines:
                await perform_check(machine)

    async def on_success(self):
        await super(ProvisionTask, self).on_success()
        for machine in self.machines:
            await machine.set('status', 'ready')
