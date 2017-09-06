"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging
import asyncio
import typing
import uuid
import abc

import cuvette.provisioners as provisioner

from concurrent.futures import ThreadPoolExecutor
from cuvette.machine import Machine
from cuvette.pool import provision_pool, failure_pool, main_pool

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
        self.loop = loop or asyncio.get_event_loop()
        self.uuid = str(uuid.uuid1())
        # Machines this task may related to, if task failed, all related machine will be
        # moved to failure pool
        self.machines = machines
        # If not None, a async task is running and when task.cancel() is called, this
        # future is cancelled
        self.future = None
        self.status = 'pending'

        Tasks[self.uuid] = self
        for machine in self.machines:
            machine['tasks'][self.uuid] = {
                'type': self.TYPE,
                'status': 'running'
            }

    async def on_done(self):
        for machine in self.machines:
            machine['tasks'].pop(self.uuid, None)

    async def on_success(self):
        logging.debug('Task {} Successed'.format(self))

    async def on_failure(self):
        logging.exception("Machine {}, Task {}, encounterd exception:".format(self.machines, self))
        self.status = 'failed'
        for machine in self.machines:
            await machine.move(failure_pool)

    def cancel(self):
        if self.future:
            return self.future.cancel()
        else:
            pass
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
            await self.on_failure()
        else:
            await self.on_success()
        finally:
            if not self.future.cancelled():
                logging.error('Coroutine leaked with {}'.format(self))
                self.future.cancel()
            self.future = None
            await self.on_done()

    @abc.abstractmethod
    async def routine(self, timeout=5):
        """
        The real task routine each subclass should implement
        """
        pass

    def __repr__(self):
        return "<{} Task UUID:{}>".format(self.TYPE, self.uuid)


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
            await machine.save(provision_pool)
        await self.provisioner.provision(self.machines, sanitized_query)
        for machine in self.machines:
            await perform_check(machine)
            await machine.move(main_pool)


class TeardownTask(BaseTask):
    """
    The helper task to teardown a machine
    """
    TYPE = 'teardown'

    def __init__(self, machines: typing.List[Machine], *args, **kwargs):
        super(TeardownTask, self).__init__(machines, *args, **kwargs)

    async def routine(self):
        sanitized_query = sanitize_query(self.query, self.provisioner.accept)
        for machine in self.machines:
            self.provisioner = provisioner.Provisioners[machine['provisioner']]
            machine['provisioner'] = self.provisioner.name
            await machine.save(provision_pool)
        await self.provisioner.provision(self.machines, sanitized_query)
        for machine in self.machines:
            await perform_check(machine)
            await machine.move(main_pool)

    async def on_success(self):
        for machine in self.machines:
            await machine.delete()
