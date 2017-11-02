"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging

import cuvette.provisioners as provisioner

from cuvette.tasks import BaseTask

logger = logging.getLogger(__name__)


class TeardownTask(BaseTask):
    """
    The helper task to teardown a machine
    """
    TYPE = 'teardown'

    def __init__(self, machines, query, *args, **kwargs):
        super(TeardownTask, self).__init__(machines, query, *args, **kwargs)

    async def routine(self):
        provisioner_machine_group = {}
        for machine in self.machines:
            provisioner_name = machine['provisioner']
            provisioner_machine_group.setdefault(provisioner_name, []).append(machine)

        for provisioner_name, machines in provisioner_machine_group.items():
            await provisioner.Provisioners.get(provisioner_name).teardown(machines, {})

    async def on_success(self):
        for machine in self.machines:
            await machine.delete()
