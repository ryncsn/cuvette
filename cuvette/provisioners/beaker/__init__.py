"""
Plugin loader
"""
import typing
import logging

from cuvette.provisioners.base import ValidateError, ProvisionerBase
from cuvette.machine import Machine

from .beaker import query_to_xml, execute_beaker_job, parse_machine_info
from .convertor import ACCEPT_PARAMS


class Provisioner(ProvisionerBase):
    name = 'beaker'
    accept = ACCEPT_PARAMS

    def avaliable(query: dict):
        """
        If given query is acceptable by this provisioner
        """
        try:
            query_to_xml(query)
        except ValidateError:
            return False
        else:
            return True

    def cost(query: dict):
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

    async def provision(machines: typing.List[Machine], query: dict):
        """
        Trigger the provision with given query
        """
        job_xml = query_to_xml(query)
        task_id, recipes = await execute_beaker_job(job_xml)
        if not len(recipes) == len(machines):
            logging.error("Expecting {} machine(s), but got {} machine(s)".format(
                 len(machines), len(recipes),
            ))
        for idx, recipe in enumerate(recipes):
            machine_info = await parse_machine_info(recipe)
            machines[idx].update(machine_info)
            machines[idx].setdefault('beaker', {})['task_id'] = task_id

    async def teardown(machine: Machine, query: dict):
        """
        Trigger the provision with given query
        """
        raise NotImplementedError()

    async def is_teareddown(machine: Machine, query: dict):
        """
        Trigger the provision with given query
        """
        raise NotImplementedError()
