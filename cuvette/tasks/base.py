"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging
import asyncio
import abc

from uuid import uuid1
from concurrent.futures import ThreadPoolExecutor
from cuvette.utils import sanitize_query

logger = logging.getLogger(__name__)


Tasks = {}  # Current tasks in ths evenloop


class Executor(ThreadPoolExecutor):
    def __init__(self, *args, **kwargs):
        super(Executor, self).__init__(*args, **kwargs)
        self.uuid = str(uuid1())


class BaseTask(object, metaclass=abc.ABCMeta):
    """
    Used to keep tracking asyncio task so we can cancel it when we want.

    Also sub classes inherit from this class will realize some logic to help
    caller to execute task on machine (Eg. provision task, transform task, reserve task).
    Task should be stateless,
    """
    TYPE = 'base'
    PARAMETERS = {}

    def __init__(self, machines, query: dict=None, loop=None, uuid=None, context=None):
        self.uuid = uuid or str(uuid1())
        self.resume = False
        self.loop = loop or asyncio.get_event_loop()
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
        self.query = sanitize_query(query, self.PARAMETERS)

        Tasks[self.uuid] = self

    @classmethod
    async def resume(cls, uuid, query, machines, *args, **kwargs):
        task = cls(machines, query, *args, **kwargs, uuid=uuid)
        task.status = 'resume'
        task.machines = machines
        task.resume = True
        Tasks[task.uuid] = task
        await task._save_task()
        return task

    async def _save_task(self):
        for machine in self.machines:
            await machine.set('tasks.{}'.format(self.uuid), {
                'query': self.query,
                'type': self.TYPE,
                'status': self.status,
            })

    async def _delete_task(self):
        for machine in self.machines:
            await machine.unset('tasks.{}'.format(self.uuid))

    async def on_done(self):
        pass

    async def on_start(self):
        pass

    async def on_success(self):
        pass

    async def on_failure(self):
        pass

    def cancel(self):
        if self.future:
            return self.future.cancel()
        else:
            return False

    async def run(self):
        """
        Run the task,
        If anything went wrong throw the machine to the failure_pool
        and mark the machine as failed.
        """
        self.status = 'running'
        logger.debug('Task {} Started.'.format(self))
        await self.on_start()
        await self._save_task()
        try:
            if self.resume:
                self.future = asyncio.ensure_future(self.resume_routine())
            else:
                self.future = asyncio.ensure_future(self.routine())
            await self.future
        except Exception as error:
            logger.exception("Task {}, Machine {} failed, encounterd exception:".format(self, self.machines))
            self.cancel()
            self.status = 'failed'
            for machine in self.machines:
                await machine.fail()
            await self.on_failure()
        else:
            logger.debug('Task {} Successed and removed.'.format(self))
            await self.on_success()
            await self._delete_task()
        finally:
            try:
                if not self.future.done() and not self.future.cancelled():
                    logger.error('Coroutine leaked with {}'.format(self))
                    self.future.cancel()
                self.future = None
                logger.info('Task {} Done and removed.'.format(self))
                await self.on_done()
                await self._delete_task()
            except Exception as error:
                for machine in self.machines:
                    await machine.fail(error)

    @abc.abstractmethod
    async def routine(self, timeout=5):
        """
        The real task routine each subclass should implement.
        """
        pass

    @abc.abstractmethod
    async def resume_routine(self, timeout=5):
        """
        Resume the task if it's interrupted by application restart
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
