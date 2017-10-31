"""
Utils for cuvette
"""
import typing
import datetime
import inspect
import importlib
import glob
import os

from .exceptions import ValidateError


def find_all_sub_module(init_path: str, exclude=[], extra=[]):
    """
    Find all module/py file in a folder which given __init__.py file belongs to.
    """
    modules = glob.glob(os.path.dirname(init_path) + "/*.py")
    dir_modules = glob.glob(os.path.dirname(init_path) + "/*/__init__.py")
    module_names = [os.path.basename(f)[:-3] for f in modules]
    module_names.extend([os.path.basename(os.path.dirname(f)) for f in dir_modules])
    return list(
        set(module_names) - {'__init__'} - set(exclude) | set(extra)
    )


def load_all_sub_module(module_name: str, submodules: typing.List[str]=None):
    """
    Find all module/py file in a folder which given __init__.py file belongs to.
    """
    module = importlib.import_module(module_name)
    return dict([(name, importlib.import_module("{}.{}".format(module_name, name)))
                 for name in submodules or module.__all__])


def type_to_string(type_):
    if type_ is str:
        return 'str'
    elif type_ is float:
        return 'float'
    elif type_ is int:
        return 'int'
    elif type_ is list:
        return 'list'
    elif type_ is bool:
        return 'bool'
    elif type_ is None:
        return None
    elif type_ is datetime.datetime:
        return 'datetime'
    elif type_ is datetime.date:
        return 'date'
    elif callable(type_):
        return 'function'
    else:
        raise RuntimeError('Unrecognized type %s' % type_)


def format_to_json(data, failover=None):
    """Format into json and load lazy-loading attr to prevent stall"""
    failover = failover or str
    if isinstance(data, (int, float, str)):
        return data
    elif isinstance(data, dict):
        return dict([(k, format_to_json(v, failover=failover)) for k, v in data.items()])
    elif hasattr(data, 'as_dict'):
        return data.as_dict()
    elif hasattr(data, '__iter__') and not inspect.isclass(data):
        return [format_to_json(_value, failover=failover) for _value in data]
    else:
        return failover(data)


def parse_request_params(http_args: dict):
    """
    Convert a Multidict of request params into a dict using custom rule.
    No '[' or ']' allowed in string.

    Example URL param:
    ?magic=1&cpu.num:gt=1&cpu.model:in[]=41&cpu.model:in[]=42&cpu.model:in[]=43&extra_device[gpu.vendor]=nvdia
    Which will be parsed into a dict by the server, this function accepts that dict.

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


def sanitize_query(query: dict, accept_params: dict):
    """
    Take a query and a dict describing the required format of the query,
    check for mistake for format the query.

    If there are some critical problem can be fixed, will raise an Exception.

    Will override the origin content in query.

    Expected format for accept_params:
    {
        'param-name': {
            'type': bool,
            'ops': ['$eq', '$lte', '$gt'],
            'default': true,
            'description': 'Optional decription',
        },
        'param-name2': {
            'type': str,
            'ops': [None],
            'default': lambda query: str(query.get('param-name', 'debug')),
        },
    }

    Expected format for query:
    {
        'param-name': {
            '$eq': true,
        },
        'param-name2': 'debug',
    }
    """
    _query = query.copy()

    for key, params in accept_params.items():
        allowed_type = params.get('type', None)
        allowed_ops = params.get('ops', None)
        default = params.get('default', None)
        item = _query.pop(key,
                          default(query) if callable(default)
                          else default)
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
        elif item is not None:
            if allowed_ops is None or None in allowed_ops:
                query[key] = item
            else:  # TODO Support other ops
                query[key] = {
                    '$eq': item
                }
    return query
