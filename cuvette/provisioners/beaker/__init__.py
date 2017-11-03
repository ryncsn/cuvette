"""
Plugin loader
"""
import logging

from cuvette.provisioners.base import ProvisionerBase
from cuvette.utils.exceptions import ValidateError

from .beaker import query_to_xml, execute_beaker_job, parse_machine_info, cancel_beaker_job
from .convertor import ACCEPT_PARAMS

logger = logging.getLogger(__name__)

DEFAULT_LIFE_SPAN = 86400


class Provisioner(ProvisionerBase):
    NAME = 'beaker'
    PARAMETERS = ACCEPT_PARAMS

    def __init__(self):
        pass

    def avaliable(self, query: dict):
        """
        If given query is acceptable by this provisioner
        """
        try:
            query_to_xml(query)
        except ValidateError:
            return False
        else:
            return True

    def cost(self, query: dict):
        """
        How much time is likely to be costed provision a machine
        matches given query
        """
        try:
            query_to_xml(query)
        except ValidateError:
            return float('inf')
        else:
            return 100

    async def provision(self, machines, sanitized_query: dict):
        """
        Trigger the provision with given query
        """
        job_xml = query_to_xml(sanitized_query)
        job_id, recipes = await execute_beaker_job(job_xml)
        if not len(recipes) == len(machines):
            logger.error("Expecting {} machine(s), but got {} machine(s)".format(
                 len(machines), len(recipes),
            ))
        for idx, recipe in enumerate(recipes):
            machine_info = await parse_machine_info(recipe)
            machines['lifespan'].sanitized_query.get('lifespan', DEFAULT_LIFE_SPAN)
            machines[idx].update(machine_info)
            machines[idx].meta['beaker-job-id'] = job_id

    async def teardown(self, machines, query: dict):
        """
        Teardown a machine provisioned from beaker,
        If user have deployed some service need to be teared down,
        they should teardown the service by themselves.
        """
        # TODO: Delete all machine with beaker-job-id, when deleting one machine of a
        # job which requested multiple machines.
        jobs = set()
        for machine in machines:
            jobs.add(machine.meta['beaker-job-id'])
        for job in jobs:
            await cancel_beaker_job(job)

    async def is_teareddown(self, machine, meta: dict, query: dict):
        """
        Trigger the provision with given query
        """
        raise NotImplementedError()
