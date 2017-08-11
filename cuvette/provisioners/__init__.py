"""
Plugin loader
"""
import abc
from cuvette.utils import find_all_sub_module

__all__ = find_all_sub_module(__file__)


ALWAYS_GREEDY = True
ALWAYS_UNTRUST = True


class ValidateError(Exception):
    """
    Exception to be raised when avaliable / cost is called and
    meet any illegal requirement for that provisioner.
    """
    pass


class ProvisionerBase(metaclass=abc.ABCMeta):
    name = abc.abstractproperty()

    @abc.abstractmethod
    def avaliable(params: dict):
        """
        If given params is acceptable by this provisioner
        """
        pass

    @abc.abstractmethod
    def cost(params: dict):
        """
        How much time is likely to be costed provision a machine
        matches given params
        """
        pass

    @abc.abstractmethod
    async def provision(params: dict):
        """
        Trigger the provision with given params
        """
        pass

    @abc.abstractmethod
    async def teardown(params: dict):
        """
        Trigger the provision with given params
        """
        pass
