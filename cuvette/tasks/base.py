"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging
import asyncio
import uuid
import abc

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# TODO: in db
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
    Task should be stateless,
    """
    TYPE = 'base'

    def __init__(self, machines, query: dict=None, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.uuid = str(uuid.uuid1())
        # Machines this task related to, if task failed, all related machine will be
        # moved to failure pool
        self.machines = machines
        # If not None, a async task is running and when task.cancel() is called, this
        # future is cancelled
        self.future = None
        # Task status, task should be reentrant, but we still keep a status attribute for now
        # for easier tracking, status should be pending, running, success, failed
        self.status = 'pending'
        # the query object that issued this task, could be None for pool scheduled task
        self.query = query
        # Some metadata that could be used for task routine and reentrant
        self.meta = {}

        Tasks[self.uuid] = self
        for machine in self.machines:
            machine['tasks'][self.uuid] = {
                'type': self.TYPE,
                'status': self.status,
                'meta': self.meta,
            }

    async def _save_task(self):
        for machine in self.machines:
            machine['tasks'][self.uuid] = {
                'type': self.TYPE,
                'status': self.status,
                'meta': self.meta,
            }
            await machine.save()

    async def _delete_task(self):
        for machine in self.machines:
            machine['tasks'].pop(self.uuid, None)
            await machine.save()

    async def on_done(self):
        logger.info('Task {} Done and removed.'.format(self))

    async def on_start(self):
        logger.debug('Task {} Started.'.format(self))
        await self._save_task()

    async def on_success(self):
        logger.debug('Task {} Successed.'.format(self))
        await self._delete_task()

    async def on_failure(self):
        logger.exception("Machine {}, Task {}, encounterd exception:".format(self.machines, self))
        self.cancel()
        self.status = 'failed'
        for machine in self.machines:
            await machine.fail()

    def cancel(self):
        if self.future:
            return self.future.cancel()
        else:
            pass
        return True

    async def run(self):
        """
        Run the task,
        If anything went wrong throw the machine to the failure_pool
        and mark the machine as failed.
        """
        self.status = 'running'
        await self.on_start()
        try:
            self.future = asyncio.ensure_future(self.routine())
            await self.future
        except Exception as error:
            await self.on_failure()
        else:
            await self.on_success()
        finally:
            if not self.future.done() and not self.future.cancelled():
                logger.error('Coroutine leaked with {}'.format(self))
                self.future.cancel()
            self.future = None
            await self.on_done()

    @abc.abstractmethod
    async def routine(self, timeout=5):
        """
        The real task routine each subclass should implement.
        """
        pass

    def conflict_with(task):
        """
        If this task conflict with another task, if not they could be run at the same time.
        Return true by default so all tasks are exlusive
        """
        return True

    def __repr__(self):
        return "<{} Task UUID:{}>".format(self.TYPE, self.uuid)
