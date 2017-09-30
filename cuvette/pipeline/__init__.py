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
from cuvette.utils import format_to_json, type_to_string


Inspectors = inspectors.Inspectors
InspectorsParameters = inspectors.Parameters
Provisioners = provisioners.Provisioners
ProvisionersParameters = provisioners.Parameters
Transformers = transformers.Transformers


logger = logging.getLogger(__name__)


def setup_parameters():
    """
    Check and setup parameters that could be accept
    """
    for provisioner in Provisioners.values():
        for param_name, param_meta in provisioner.accept.items():
            inspecter_param_meta = InspectorsParameters.get(param_name)
            if not inspecter_param_meta:
                logger.error('Parameter "%s" of provisioner "%s" is not inspected by any inspector',
                             param_name, provisioner.name)
                InspectorsParameters[param_name] = param_meta.copy()
                InspectorsParameters[param_name]['source'] = {
                    'type': 'provisioner',
                    'name': param_name
                }
            else:
                KEYS_TO_CHECK = ['type']
                for key in KEYS_TO_CHECK:
                    if inspecter_param_meta.get(key) != param_meta.get(key):
                        logger.error('Different declaration for %s\n'
                                     'inspectors give:\n %s\n'
                                     'provisioner %s gives:\n %s\n',
                                     param_name, inspecter_param_meta, provisioner.name, param_meta)
                        break


Parameters = setup_parameters()


DEFAULT_POOL_SIZE = 50


def format_parameters(parameters: dict):
    return format_to_json(parameters, failover=type_to_string)


class PipelineException(Exception):
    pass


class Pipeline(object):
    """
    Do the most common operation, provision, reserve, teardown
    """
    def __init__(self, request):
        """
        Wrap a request object with pipeline
        """
        self.request = request

    async def query(self, request, query_params: dict):
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
                logger.warn('Passing through parameter "%s", as no inspector for it', key)

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
            logger.debug('Selected provisioner %s to provision new machine', min_cost_provisioner.name)
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
                        logger.error('Dead task {} dropped'.format(task_uuid))
                    else:
                        task.cancel()
            Provisioners[provisioner].teardown(machines)
            map(machines, lambda x: x.delete())
