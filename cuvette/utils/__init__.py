"""
Utils for cuvette
"""
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
