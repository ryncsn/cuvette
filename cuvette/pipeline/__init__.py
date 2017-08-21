"""
Only have one pipeline, so it's singleton

Maybe will extend it later
"""
import asyncio

import cuvette.inspectors as inspectors
import cuvette.transformers as transformers
import cuvette.provisioners as provisioners

from cuvette.machine import main_pool, Machine
from cuvette.pipeline.magic import Magic
from cuvette.pipeline.task import ProvisionTask


Inspectors = inspectors.Inspectors
Transformers = transformers.Transformers
Provisioners = provisioners.Provisioners


def parse_url(http_args: dict):
    """
    Convert a HTTP Get URL into dict using custom rule.

    No '[' or ']' allowed in string.

    Example URL param:

    ?magic=1&cpu.num:gt=1&cpu.model:in[]=41&cpu.model:in[]=42&cpu.model:in[]=43&extra_device[gpu.vendor]=nvdia

    which will should be parsed into a multidict, then this function will parse the multidict again.
    """

    # TODO
    def _token_parser(string: str):
        layers = []
        brackets = []
        token = ''
        for _c in string:
            if _c == '[':
                if token:
                    layers.append(token)
                    token = ''
                brackets.append(_c)
            elif _c == ']':
                try:
                    closing = brackets.pop()
                    if not closing == '[':
                        raise RuntimeError()
                except (IndexError, RuntimeError):
                    raise RuntimeError('Non-closing bracket')
                layers.append(token)
                token = ''
            else:
                token += _c
            if len(brackets) > 1:
                raise RuntimeError('Multilayer brackets not allowed')
        if token:
            layers.append(token)
        return layers

    data = {}

    for key, value in http_args.items():
        node = data
        layers = _token_parser(key)

        if layers[0] == '':
            raise RuntimeError('Root query object must be dict')

        for key, next_key in zip(layers[:-1], layers[1:]):
            if key == '':
                raise RuntimeError('Currently, list of object is not supported, [] must be at the end of param')

            next_type = dict
            if next_key == '':
                next_type = list

            node = node.setdefault(key, next_type())
            if not isinstance(node, next_type):
                raise RuntimeError('Type conflict, expecting {}, got {}'.format(next_type, type(node)))

        if layers[-1] == '':
            node.append(value)
        else:
            if node.setdefault(layers[-1], value) != value:
                raise RuntimeError('Value conflict for {}'.format(key))
    return data


def parse_query(params: dict):
    """
    Convert a Key-value dict (most likely from a HTTP GET request)
    into a MongoDB like query object,
    as there could be some special operation used by some inspector,
    only comparison is allowed.

    convert:
    {
        "magic": 1,
        "cpu.num:gt": 1,
        "cpu.num:lte": 4,
        "cpu.model:in": [41, 42, 43],
        ...
    }
    into:
    {
        "magic": 1,
        "cpu.num": {
            '$gt': 1,
            '$lte': 4,
        },
        "cpu.num": {
            '$in': [41, 42, 43],
        },
        ...
    }
    """
    ret = {}
    for field, value in params.items():
        if isinstance(value, dict):
            value = parse_query(value)
        try:
            field, op = field.split(':', 1)
            op = '$' + op if not op.startswith('$') else op
        except (KeyError, ValueError):
            field, op = field, None
        if op is None:
            if ret.setdefault(field, value) != value:
                raise RuntimeError("Query conflict '%s' and '%s', "
                                   '%s' % (ret[field]), '%s=%s' % (field, value)
                                   )
        else:
            if isinstance(ret.setdefault(field, {}), dict):
                ret[field][op] = value
            else:
                raise RuntimeError("Query conflict '%s' and '%s', "
                                   "when plain value is given extra operation is not allowed",
                                   '%s=%s' % (field, ret[field]), '%s (%s) %s' % (field, op, value)
                                   )
    return ret


def flatten_query(query: dict, force: bool = False):
    """
    Simplyfi operation '$eq'
    """
    for key, value in query.items():
        if isinstance(value, dict):
            if value.keys() == ['$eq']:
                query[key] = value.values()[0]
                continue
        if force:
            raise RuntimeError('{} only accept plain value'.format(key))


class Pipeline(object):
    def __init__(self, request):
        self.request = request

    async def query(self, data: dict):
        query_params = parse_query(parse_url(data))

        # Magic deal with the problem that browser keep sending request
        # Result in tons of request job
        magic = Magic(self.request)

        machines = await magic.query(query_params)

        if not machines:
            composed_filter = {}
            composed_filter.update(await magic.create_filter(query_params))
            for inspector in Inspectors.values():
                composed_filter.update(inspector.create_filter(query_params))
            machines = [Machine.load(m) for m in await main_pool.find(composed_filter).to_list(None)]

        if machines:
            return [m.to_json() for m in machines]

        return None

    async def provision(self, data: dict):
        """
        If provision is done within 5s, return List[machine], True
        else return List[machine], False
        """
        machine = Machine()
        await Magic(self.request).mark_magic(machine)
        query_params = parse_query(parse_url(data))

        min_cost, min_cost_provisioner = float('inf'), None

        for provisioner in Provisioners.values():
            if provisioner.avaliable(query_params):
                if provisioner.cost(query_params) < min_cost:
                    min_cost_provisioner = provisioner

        if min_cost_provisioner:
            provision_task = ProvisionTask([machine], min_cost_provisioner, query_params)
            # If the provision finished in 5s, return it.
            finished, pending = await asyncio.wait([provision_task.run()], timeout=5)
            if finished:
                return [machine.to_json()]
            else:
                return [machine.to_json()]
        else:
            return {'message': 'invalid request'}

    async def teardown(self, data: dict):
        # query_params = parse_query(data)
        raise NotImplementedError()