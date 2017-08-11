"""
Only have one pipeline, so it's singleton

Maybe will extend it later
"""
import cuvette.inspectors as inspectors
import cuvette.transformers as transformers
import cuvette.provisioners as provisioners


def parse_url(params: dict):
    """
    Convert a HTTP Get URL into dict using custom rule.

    Example URL param:

    ?magic=1&cpu.num:gt=1&cpu.model:in[]=41&cpu.model:in[]=42&cpu.model:in[]=43&extra_device[gpu.vendor]=nvdia
    """
    pass


def parse_query(params: dict):
    """
    Convert a Key-value dict (most likely from a HTTP GET request)
    into a MongoDB like query object, not exactly mongodb query object
    as there could be some special operation used by some inspector but
    not recognized by MongoDB.

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
        try:
            field, op = field.split(':', 1)
            op = '$' + op if not op.startswith('$') else op
        except KeyError:
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
    def __init__(self):
        pass

    def request(self, data: dict):
        query_params = parse_query(data)
        pass


main_pipeline = Pipeline()
