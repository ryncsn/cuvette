"""
Plugin loader
"""
import asyncio
import logging

from cuvette.settings import Settings
from cuvette.provisioners.base import ProvisionerBase
from cuvette.utils.exceptions import ValidateError, ProvisionError

from .beaker import query_to_xml, pull_beaker_job, submit_beaker_job, parse_machine_info, cancel_beaker_job
from .convertor import ACCEPT_PARAMS

logger = logging.getLogger(__name__)

DEFAULT_LIFE_SPAN = 86400
BEAKER_URL = Settings.BEAKER_URL.rstrip('/')


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

    async def provision_loop(self, machines, sanitized_query, last_job_id=None):
        job_xml = query_to_xml(sanitized_query)
        recipes = None
        job_id = last_job_id
        for failure_count in range(10):
            job_id = job_id or await submit_beaker_job(machines, job_xml)
            for machine in machines:
                await machine.set('meta.beaker-job_id', job_id)
                await machine.set('meta.beaker-failure_count', failure_count)
            recipes = await pull_beaker_job(machines, job_id)
            if recipes is None and failure_count != 10:
                logger.error("Provision failed, retrying")
            elif not len(recipes) == len(machines):
                logger.error("Expecting {} machine(s), but got {} machine(s)".format(
                     len(machines), len(recipes),
                ))
                recipes = None
            else:
                break
            job_id = None

        if recipes is None:
            raise ProvisionError("Failed to retrive {} machines with given query from beaker".format(len(machines)))

        for idx, recipe in enumerate(recipes):
            machine_info = await parse_machine_info(recipe)
            await machines[idx].set('lifespan', sanitized_query.get('provision-lifespan', DEFAULT_LIFE_SPAN))
            await machines[idx].set(machine_info)

        return machines

    async def provision(self, machines, sanitized_query: dict):
        """
        Trigger the provision with given query
        """
        machines = await self.provision_loop(machines, sanitized_query)
        return machines

    async def resume(self, machines, sanitized_query: dict):
        """
        Trigger the provision with given query
        """
        job_id_set = set()
        for machine in machines:
            job_id_set.add(machine['meta']['beaker-job_id'])
        if len(job_id_set) != 1:
            raise RuntimeError("Can't resume multiple job at one time")
        job_id = job_id_set.pop()
        machines = await self.provision_loop(machines, sanitized_query, job_id)
        return machines

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
