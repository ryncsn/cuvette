"""
Only have one pipeline, so it's singleton

Maybe will extend it later
"""
import copy
import asyncio
import logging
import itertools

import cuvette.inspectors as inspectors
import cuvette.transformers as transformers
import cuvette.provisioners as provisioners

from cuvette.pool.machine import Machine
from cuvette.tasks import ProvisionTask, ReserveTask, Tasks


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
    # use InspectorsParameters as the baseline, check and update missing ones from ProvisionersParameters
    parameters = InspectorsParameters.copy()
    for provisioner in Provisioners.values():
        for param_name, param_meta in provisioner.accept.items():
            inspecter_param_meta = parameters.get(param_name)
            if not inspecter_param_meta:
                logger.error('Parameter "%s" of provisioner "%s" is not inspected by any inspector',
                             param_name, provisioner.name)
                parameters[param_name] = param_meta.copy()
                parameters[param_name]['source'] = {
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
    return parameters


Parameters = setup_parameters()


DEFAULT_POOL_SIZE = 50


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

    async def query(self, query_params: dict, count=None):
        """
        Return if there is any machine matches required query or
        return the already provisining machine.
        """
        query_params = copy.deepcopy(query_params)
        composed_filter = {}
        for inspector in Inspectors.values():
            composed_filter.update(inspector.hard_filter(query_params))

        return [Machine(m) for m in await Machine.find_all(composed_filter, count=count)]

    async def provision(self, query_params: dict, timeout=5, count=None):
        """
        Block for timeout time for the provision to finish,
        else run the task async.
        """
        # Currently, only return one machine one time
        machine = Machine()

        for inspector in Inspectors.values():
            query_params = inspector.provision_filter(query_params)

        await self.request['magic'].pre_provision(machine, query_params)

        min_cost_provisioner = provisioners.find_avaliable(query_params)

        if min_cost_provisioner:
            logger.debug('Selected provisioner %s to provision new machine', min_cost_provisioner.name)
            provision_task = ProvisionTask([machine], min_cost_provisioner, query_params)
            finished, pending = await asyncio.wait([provision_task.run()], timeout=timeout)
            if finished:
                return [machine]
            else:
                return [machine]
        else:
            return {'message': 'Failed to provision a machine, as no one machine matched your need, '
                    'or there are zero machine.'}

    async def reserve(self, query_params: dict, reserve_time=3600, count=None, greedy=False):
        """
        Reserve a machine, if greedy, reserve as much as possible without checking
        """
        try:
            reserve_time = int(query_params.pop('reserve_time', reserve_time))
        except Exception:
            raise RuntimeError('reserve_time not specified or illegal')
        machines = await self.query(query_params, count=count)
        if not greedy:
            for machine in machines:
                if machine['tasks']:
                    raise RuntimeError("Can't reserve machine {} {} with tasks".format(
                        machine.get('hostname', 'no-host'), machine.get('magic', 'no-magic')))
        reserve_task = ReserveTask(machines, reserve_time)
        asyncio.ensure_future(reserve_task.run())
        return machines

    async def release(self, query_params: dict):
        """
        Release a reserved machine, cancel all reserve tasks on machines
        """
        machines = await self.query(query_params)
        for machine in machines:
            for task in machine.tasks:
                if task.type == 'reserve':
                    task.cancel()

    async def inspect(self, query_params: dict):
        """
        Inspect some machines
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
