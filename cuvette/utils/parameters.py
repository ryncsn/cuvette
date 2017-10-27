"""
Check parameters shared between modules
"""

import logging

logger = logging.getLogger(__name__)

REQUIRED_KEYS = ['type']
CONSISTENT_KEYS = ['type']
ACCEPTABLE_KEYS = ['type', 'ops', 'description', 'default']
EXPOSE_KEYS = ['type', 'ops', 'description', 'default']
DEFAULT_VALUES = {
    "op": None  # Nones mean not checking, [None] means plain value
}


def make_op_consistent(param_name, parent_meta, child_meta):
    """
    To make op consitent between two module, choose a parent and child one,
    as long as child one'op is covered by parent one, we consider it legit.
    # TODO: could make it better by make sure all parent's op could be translate
    into child's ones.
    """
    op1 = parent_meta.get('ops', None)
    op2 = child_meta.get('ops', None)

    if op1 is None or op2 is None:
        return op1 or op2

    if set(op1) < set(op2):
        logger.error("parameter %s from %s and %s have different limit of ops!",
                     param_name, parent_meta['source'], child_meta['source'])

    if not set(op1) & set(op2):
        raise RuntimeError("Two param set's op not match!")

    return op1


def consistent_updater(param_name, existing_parameter, parameter):
    for key in parameter.keys():
        if key == 'ops':
            existing_parameter['ops'] = make_op_consistent(param_name, existing_parameter, parameter)
        elif key in CONSISTENT_KEYS:
            if existing_parameter.setdefault(key, parameter[key]) != parameter[key]:
                raise RuntimeError("Inconsistent parameter %s from %s (%s) to %s (%s)",
                                   param_name,
                                   existing_parameter['source'], existing_parameter[key],
                                   parameter['source'], parameter[key])
        else:
            existing_parameter[key] = parameter[key]


def get_all_parameters(modules, section,
                       consistent=True, override=True, conflict=False,
                       exclude_keys=None,
                       param_getter=None, name_getter=None):
    """
    Get parameters from a list of same kind of modules
    """
    ret = {}
    name_getter = name_getter or (lambda module: str(module))
    param_getter = param_getter or (lambda module: module.PARAMETERS)
    exclude_keys = exclude_keys or []
    for module in modules:
        module_name = name_getter(module)
        param_source = {
            'type': section,
            'name': module_name,
        }
        for param_name, param_meta in param_getter(module).items():
            existing_param_meta = ret.get(param_name, None)

            if existing_param_meta is None:
                existing_param_meta = ret[param_name] = {}
            else:
                if conflict:
                    raise RuntimeError("Duplicated parameter %s from %s and %s" %
                                       (param_name, existing_param_meta['source'], param_source))

            if consistent:
                for key in CONSISTENT_KEYS:  # Skip op check
                    existing = existing_param_meta.get(key, None)
                    param = param_meta.get(key, None)
                    if existing is not None and param is not None and existing != param:
                        raise RuntimeError("Inconsistent parameter %s from %s and %s" %
                                           (param_name, existing_param_meta['source'], param_source))

            ret.setdefault(param_name, {}).setdefault('source', [])

            for key, value in param_meta.items():
                if key not in ACCEPTABLE_KEYS or key in exclude_keys:
                    logger.error("Unaccptable key %s in param %s, from %s",
                                 key, param_name, param_source)
                    continue

                if key == 'ops':
                    # Always use superset of op when loading:
                    # if conflict = true, following condition is never used
                    # else, if we should always use super set so make sure all op belong to this
                    # king of module is discovered.
                    ops = param_meta.get('ops')
                    existing_ops = existing_param_meta.get('ops')
                    if ops is None or existing_ops is None:
                        new_ops = ops or existing_ops
                    else:
                        new_ops = set(ops + existing_ops)
                    existing_param_meta['ops'] = new_ops
                elif not override:
                    existing_param_meta.setefault(key, value)
                else:
                    existing_param_meta[key] = value

            ret[param_name]['source'].append(param_source)
    return ret


def check_and_merge_parameter(base_parameters, parameters):
    """
    Merge two parameter set
    """
    for param_name, param_meta in parameters.items():
        base_meta = base_parameters.setdefault(param_name, {})
        consistent_updater(param_name, base_meta, param_meta)
