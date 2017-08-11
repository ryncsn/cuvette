"""
Utils for cuvette
"""
import glob
import os


def find_all_sub_module(init_path: str):
    """
    Find all module/py file in a folder which given __init__.py file belongs to.
    """
    modules = glob.glob(os.path.dirname(init_path) + "/*.py")
    return [os.path.basename(f)[:-3]
            for f in modules if os.path.isfile(f) and not f.endswith('__init__.py')]
