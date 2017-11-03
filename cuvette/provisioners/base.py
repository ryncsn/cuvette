import abc

ALWAYS_GREEDY = True
ALWAYS_UNTRUST = True


class ProvisionerBase(metaclass=abc.ABCMeta):
    PARAMETERS = abc.abstractproperty()
    NAME = abc.abstractproperty()
    """
    What parameters this provisioner accepts
    """

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
    async def provision(machines, meta: dict, query: dict):
        """
        Trigger the provision with given params
        """
        pass

    @abc.abstractmethod
    async def teardown(machines, meta: dict, query: dict):
        """
        Teardown a machine, this function might be called multiple time for a single machine
        """
        pass

    @abc.abstractmethod
    async def is_teareddown(machines, meta: dict, query: dict):
        """
        Judge if a machine have been release by third part.
        """
        pass
