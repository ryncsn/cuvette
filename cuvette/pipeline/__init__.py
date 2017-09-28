"""
Only have one pipeline, so it's singleton

Maybe will extend it later
"""
import asyncio
import logging
import itertools

import cuvette.inspectors as inspectors
import cuvette.transformers as transformers
import cuvette.provisioners as provisioners

from cuvette.pool.machine import Machine
from cuvette.pipeline.task import ProvisionTask, Tasks


Inspectors = inspectors.Inspectors
InspectorsParameters = inspectors.Parameters
Transformers = transformers.Transformers
Provisioners = provisioners.Provisioners


DEFAULT_POOL_SIZE = 50


def PipelineException(Exception):
    pass


class Pipeline(object):
    """
    When a request comes to pipeline, a pipeline object is created.
    """
    def __init__(self, request):
        self.request = request

    async def query(self, query_params: dict):
        """
        Return if there is any machine matches required query or
        return the already provisining machine.
        """
        composed_filter = {}
        for inspector in Inspectors.values():
            composed_filter.update(inspector.create_filter(query_params))

        # TODO: sanitize, it's dangerous
        for key, value in query_params.items():
            if key not in InspectorsParameters:
                composed_filter[key] = value
                logging.warn('Passing through parameter "%s", as no inspector for it', key)

        return [Machine(m) for m in await Machine.find_all(composed_filter)]

    async def provision(self, query_params: dict, timeout=5):
        """
        Block for timeout time for the provision to finish,
        else run the task async.
        """
        # Currently, only return one machine one time
        machine = Machine()

        await self.request['magic'].pre_provision(machine, query_params)

        min_cost_provisioner = provisioners.find_avaliable(query_params)

        if min_cost_provisioner:
            provision_task = ProvisionTask([machine], min_cost_provisioner, query_params)
            finished, pending = await asyncio.wait([provision_task.run()], timeout=timeout)
            if finished:
                return [machine.to_json()]
            else:
                return [machine.to_json()]
        else:
            return {'message': 'Failed to provision a machine, as no one machine matched your need, '
                    'or there are zero machine.'}

    async def reserve(self, query_params: dict):
        """
        Reserve a machine
        """
        pass

    async def release(self, query_params: dict):
        """
        Release a reserved machine
        """
        pass

    async def teardown(self, query_params: dict):
        """
        Teardown a machine, cancel all running tasks then call the provisioner to tear it down properly.
        """
        machines = await self.query(query_params)
        if not machines:
            raise PipelineException("Can't find any machine to teardown")
        for provisioner, machines in itertools.groupby(machines, lambda x: x['provisioner']):
            for machine in machines:
                for task_uuid, task_meta in machine.tasks.items():
                    task = Tasks.get(task_uuid)
                    if not task:
                        logging.error('Dead task {} dropped'.format(task_uuid))
                    else:
                        task.cancel()
            Provisioners[provisioner].teardown(machines)
            map(machines, lambda x: x.delete())
