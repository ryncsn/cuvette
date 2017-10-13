import abc
import typing


ALWAYS_GREEDY = True
ALWAYS_UNTRUST = True


class ValidateError(Exception):
    """
    Exception to be raised when avaliable / cost is called and
    meet any illegal requirement for that provisioner.
    """
    pass


def sanitize_query(query: dict, accept_params: dict):
    _query = query.copy()
    for key, params in accept_params.items():
        allowed_type = params.get('type', None)
        allowed_ops = params.get('ops', None)
        item = _query.pop(key, {})
        if isinstance(item, dict):
            for op, value in item.items():
                if allowed_ops is not None and op not in allowed_ops:
                    raise ValidateError('Unaccptable operation {} for {}'.format(op, key))
                if allowed_type is not None:
                    if isinstance(value, allowed_type):
                        continue
                    try:
                        query[key][op] = allowed_type(value)
                    except Exception:
                        raise ValidateError('Unaccptable value type {} for {}'.format(type(value), key))
        elif isinstance(item, str):
            if allowed_ops is not None and '$eq' in allowed_ops:
                query[key] = {'$eq': item}
    return query


class ProvisionerBase(metaclass=abc.ABCMeta):
    name = abc.abstractproperty()
    accept = abc.abstractproperty()
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
