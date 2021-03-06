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

from cuvette.machine import Machine
from cuvette.tasks import ProvisionTask, ReserveTask, retrive_tasks_from_machine
from cuvette.tasks import Parameters as TaskParameters
from cuvette.utils.parameters import check_and_merge_parameter


Inspectors = inspectors.Inspectors
InspectorsParameters = inspectors.Parameters
Provisioners = provisioners.Provisioners
ProvisionersParameters = provisioners.Parameters
Transformers = transformers.Transformers


logger = logging.getLogger(__name__)


PIPELINE_PARAMETERS = {
    'count': {
        'type': int,
        'ops': [None],
        'default': 1,
    }
}


def setup_parameters():
    """
    Check and setup parameters from inspectors, provisioners, and avaliable tasks
    make sure they are correct, and collect all info about parameters
    """
    pipiline_parameters = PIPELINE_PARAMETERS.copy()
    inspector_parameters = InspectorsParameters.copy()
    provisioner_parameters = ProvisionersParameters.copy()
    task_parameters = TaskParameters.copy()

    # Append inspector_parameters first
    parameters = {}

    check_and_merge_parameter(parameters, pipiline_parameters)
    check_and_merge_parameter(parameters, inspector_parameters)
    check_and_merge_parameter(parameters, provisioner_parameters)
    check_and_merge_parameter(parameters, task_parameters)

    return parameters


Parameters = setup_parameters()


DEFAULT_POOL_SIZE = 50


class PipelineException(Exception):
    pass


class Pipeline(object):
    """
    Do the most common operation, provision, reserve, teardown

    Take a query ->
        parse with inspectors -> query for valid machine ->
        parse with transformers -> get cost A ->
        parse with provisioners -> get cost B ->
        compare cost -> provision or transform machine
    """
    def __init__(self, request):
        """
        Wrap a request object with pipeline
        """
        self.request = request

    async def query(self, query_params: dict, nocount=None):
        """
        Return if there is any machine matches required query or
        return the already provisining machine.
        """
        count = query_params['count']

        query_params = copy.deepcopy(query_params)
        composed_filter = {}

        for inspector in Inspectors.values():
            composed_filter.update(inspector.hard_filter(query_params))

        machines = await Machine.find_all(
            self.request.app['db'],
            composed_filter, None if nocount else count)

        return machines

    async def provision(self, query_params: dict, timeout=5, count=None):
        """
        Block for timeout time for the provision to finish,
        elsy run the task async.
        """

        if not await self.request['magic'].allow_provision(query_params):
            return []

        min_cost_provisioner = provisioners.find_avaliable(query_params)

        count = query_params['count']

        for inspector in Inspectors.values():
            query_params = inspector.provision_filter(query_params)

        machines = [Machine(self.request.app['db']) for _ in range(count)]

        try:
            # Magic deal with the problem that browser keep sending request
            # Result in tons of request job
            await self.request['magic'].pre_provision(machines, query_params)
            for machine in machines:
                await machine.save()

            if min_cost_provisioner:
                logger.debug('Selected provisioner %s to provision new machine', min_cost_provisioner.NAME)
                provision_task = ProvisionTask(machines, query_params, min_cost_provisioner)
                finished, pending = await asyncio.wait([provision_task.run()], timeout=timeout)
                if finished:
                    return machines
                else:
                    return machines
            else:
                raise RuntimeError('Failed to provision a machine, as no one machine matched your need, '
                                   'or there are zero machine.')
        except RuntimeError as error:
            for machine in machines:
                await machine.delete()
            raise

    async def reserve(self, query_params: dict):
        """
        Reserve a machine, if greedy, reserve as much as possible without checking
        """
        machines = await self.query(query_params)
        for machine in machines:
            if machine['tasks']:
                raise RuntimeError("Can't reserve machine {} {} with tasks".format(
                    machine.get('hostname', 'no-host'), machine.get('magic', 'no-magic')))
        reserve_task = ReserveTask(machines, query_params)
        asyncio.ensure_future(reserve_task.run())
        return machines

    async def release(self, query_params: dict):
        """
        Release a reserved machine, cancel all reserve tasks on machines
        """
        machines = await self.query(query_params)
        ret = []
        for machine in machines:
            released = False
            for task in await retrive_tasks_from_machine(machine):
                if task.TYPE == 'reserve':
                    task.cancel()
                    released = True
            if released:
                ret.append(machine)
        return ret

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
                await machine.mark_delete()  # only mark in case some task running
                for task in await retrive_tasks_from_machine(machine):
                    task.cancel()
            await Provisioners[provisioner].teardown(machines, query_params)
        return machines
