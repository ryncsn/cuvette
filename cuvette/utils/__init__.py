"""
Utils for cuvette
"""
import datetime
import inspect
import importlib
import glob
import os


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


def load_all_sub_module(module_name: str):
    """
    Find all module/py file in a folder which given __init__.py file belongs to.
    """
    module = importlib.import_module(module_name)
    return dict([(name, importlib.import_module("{}.{}".format(module_name, name)))
                 for name in module.__all__])


def type_to_string(type_):
    if type_ is str:
        return 'str'
    elif type_ is float:
        return 'float'
    elif type_ is int:
        return 'int'
    elif type_ is list:
        return 'list'
    elif type_ is datetime.datetime:
        return 'datetime'
    elif type_ is datetime.date:
        return 'date'
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
