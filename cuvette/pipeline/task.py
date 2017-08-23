"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging
import asyncio
import typing
import uuid
import abc

from concurrent.futures import ThreadPoolExecutor
from cuvette.machine import Machine
from cuvette.machine import provision_pool, failure_pool, main_pool

from cuvette.provisioners.base import sanitize_query
from cuvette.inspectors import perform_check

Tasks = {}


class Executor(ThreadPoolExecutor):
    def __init__(self, *args, **kwargs):
        super(Executor, self).__init__(*args, **kwargs)
        self.uuid = str(uuid.uuid1())


class BaseTask(metaclass=abc.ABCMeta):
    """
    Used to keep tracking asyncio task so we can cancel it when we want.

    Also sub classes inherit from this class will realize some logic to help
    caller to execute task on machine (Eg. provision task, transform task, reserve task).
    """
    TYPE = 'base'

    def __init__(self, machines: typing.List[Machine], loop=None):
        self.loop = loop
        self.uuid = str(uuid.uuid1())
        self.machines = machines
        self.future = None
        self.status = 'pending'

        Tasks[self.uuid] = self
        for machine in self.machines:
            machine['tasks'][self.uuid] = self.TYPE

    def on_done(self):  # TODO
        pass

    def on_success(self):  # TODO
        pass

    def on_failure(self):  # TODO
        pass

    def cancel(self):
        try:
            if self.future:
                return self.future.cancel()
        finally:
            for machine in self.machines:
                machine.move(failure_pool)
        return True

    async def run(self):
        """
        Run the task
        If anything went wrong thorw the machine into the failure_pool
        """
        self.status = 'running'
        self.future = asyncio.ensure_future(self.routine())
        try:
            await self.future
        except Exception as error:
            self.status = 'failed'
            logging.exception("Machine {}, Task {}, encounterd exception:".format(self.machines, self))
        else:
            self.status = 'success'
            return self.future.result()
        finally:
            if not self.future.cancelled():
                self.future.cancel()
            self.future = None

    @abc.abstractmethod
    async def routine(self, timeout=5):
        pass


class ProvisionTask(BaseTask):
    """
    Used to keep tracking asyncio task so we can cancel it when we want.
    """
    TYPE = 'provision'

    def __init__(self, machines: typing.List[Machine], provisioner, query, loop=None):
        super(ProvisionTask, self).__init__(machines, loop)
        self.provisioner = provisioner
        self.query = query

    async def routine(self):
        sanitized_query = sanitize_query(self.query, self.provisioner.accept)
        for machine in self.machines:
            machine['provisioner'] = self.provisioner.name
            await machine.save(provision_pool)
        await self.provisioner.provision(self.machines, sanitized_query)
        for machine in self.machines:
            await perform_check(machine)
            await machine.move(main_pool)
