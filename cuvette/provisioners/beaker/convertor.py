"""
Translate query dict into beaker xml
Raise ValidateError if any query param is illegal
"""

from lxml import etree
from xml.dom import minidom
from xml.etree.ElementTree import Element

from cuvette.provisioners.base import ValidateError
from cuvette.settings import Settings


DEFAULTS = Settings.BEAKER_JOB_DEFAULTS


ACCEPT_PARAMS = {
    'system-type': {
        'type': str,
        'ops': [None],
    },
    'cpu-arch': {
        'type': str,
        'ops': [None],
    },
    'cpu-vendor': {
        'type': str,
        'ops': [None],
    },
    'cpu-model': {
        'type': str,
        'descript': 'CPU model',
        'ops': ['$eq', '$in'],
    },
    'cpu-flags': {
        'descript': 'CPU Flase need to be supported',
        'type': list,
        'ops': [None]
    },
    'memory-total_size': {
        'type': int,
        'ops': ['$eq', '$lt', '$gt', '$lte', '$gte'],
        'descript': 'Size in MB',
    },
    'disk-total_size': {
        'type': int,
        'ops': ['$eq', '$lt', '$gt', '$lte', '$gte'],
        'descript': 'Size in GB',
    },
    'disk-number': {
        'type': int,
        'ops': ['$eq', '$lt', '$gt', '$lte', '$gte'],
    },
    'numa-node_number': {
        'type': int,
        'ops': ['$eq', '$lt', '$gt', '$lte', '$gte'],
    },
    'hvm': {
        'type': bool,
        'ops': [None],
    },
    'sriov': {
        'type': bool,
        'ops': [None],
    },
    'npiv': {
        'type': bool,
        'ops': [None],
    },
    'device_drivers': {
        'type': list,
        'ops': [None],
    },
    'location': {
        'ops': [None],
    },
}


def boilerplate_job(query: dict):
    """
    Build a boilerplate beaker job xml with no recipe
    """
    job = etree.Element('job')

    """
    retention tags:
    scratch: preserve logs for 30 days
    60days: preserve logs for 60 days
    120days: preserve logs for 120 days
    active: preserve as long as associated product is active
    audit: preserve indefinitely (no automatic deletion)
    """
    job.set('retention_tag', 'scratch')

    # Group up jobs for better tracking and management
    job.set('group', DEFAULTS['job-group'])  # TODO: value from query

    whiteboard = etree.SubElement(job, 'whiteboard')
    whiteboard.text = query.get('whiteboard', DEFAULTS['job-whiteboard'])  # TODO: value from query

    return job


def fill_location(host_requires: Element, sanitized_query: dict):
    controllers = []
    location = sanitized_query.get('location', {}).get('$eq')
    host_requires.set('force', location)

    if set(sanitized_query.keys()) - {'location'}:
        raise ValidateError('When location is binded to a single host, extra params is not supported')

    and_op = etree.SubElement(host_requires, 'and')

    if controllers:
        or_op = etree.SubElement(and_op, 'or')
        for controller_name in controllers:
            controller = etree.SubElement(or_op, 'labcontroller')
            controller.set('op', '=')
            controller.set('value', controller_name)


def fill_machine_type(host_requires: Element, sanitized_query: dict):
    # Always baremetal
    system_type = etree.SubElement(host_requires, 'system_type')
    system_type.set("value", "Machine")


def fill_ks_appends(root: Element, sanitized_query: dict):
    """
    Fill ks appends element for beaker job XML according to parameters
    """
    ks_append = etree.SubElement(root, 'ks_append')
    ks_append.text = etree.CDATA(DEFAULTS['job-ksappend'])


def fill_repos(repos: Element, query: dict):
    """
    Fill repos element for beaker job XML according to parameters
    """
    repo_list = query.get('yum_repos')
    if repo_list and isinstance(repo_list, list):
        for repo_dict in repo_list:
            repo = etree.SubElement(repos, 'repo')
            repo.set('name', repo_dict['name'])
            repo.set('url', repo_dict['baseurl'])


def fill_distro_requires(root: Element, query: dict):
    """
    Fill distro requires element for beaker job XML according to parameters
    """
    and_op = etree.SubElement(root, 'and')
    requirements = ['distro_variant = Server']
    if query.get('cpu-arch'):
        requirements.append('distro_arch = ' + query.get('cpu-arch'))
    if query.get('beaker-distro'):
        requirements.append('distro_name = ' + query.get('beaker-distro'))

    for requirement in requirements:
        key, op, value = requirement.split()
        require = etree.SubElement(and_op, key)
        require.set("op", op)
        require.set("value", value)


def fill_packages(root: Element, query: dict):
    """
    Fill packages element for beaker job XML according to parameters
    """
    pkg_names = set(DEFAULTS['job-packages'])
    packages = query.get('packages')
    if packages:
        if isinstance(packages, list):
            pkg_names.extend(packages)
        else:
            raise ValidateError('Packages must be a list of package names')
    for pkg_name in pkg_names:
        package_ele = etree.SubElement(root, 'package')
        package_ele.set('name', pkg_name)


def fill_cpu(root: Element, sanitized_query: dict):
    # Process CPU models filter
    cpu_model_alias = {
        ('westmere', ): ['47', '44', '37'],
    }

    cpu_vendor_alias = {
        'amd': 'AuthenticAMD',
        'ibm': 'IBM',
        'intel': 'GenuineIntel',
    }

    cpu_models = []
    cpu_models_query = sanitized_query.get('cpu-model')
    if cpu_models_query:
        for op, value in cpu_models_query.items():
            if op == '$eq':
                cpu_models.extend(cpu_model_alias.get(value, [value]))
            else:
                cpu_models.extend(value)  # TODO

    cpu_vendor = None
    if sanitized_query.get('cpu-vendor'):
        cpu_vendor = cpu_vendor_alias.get(value, value)

    if cpu_models:
        or_op = etree.SubElement(root, 'or')
        for model_name in cpu_models:
            cpu = etree.SubElement(or_op, 'cpu')
            model = etree.SubElement(cpu, 'model')
            model.set('op', '=')
            model.set('value', model_name)

    if cpu_vendor:
        or_op = etree.SubElement(root, 'or')
        cpu = etree.SubElement(or_op, 'cpu')
        vendor = etree.SubElement(cpu, 'vendor')
        vendor.set('op', '=')
        vendor.set('value', cpu_vendor)


def fill_devices(root: Element, sanitized_query: dict):
    device_drivers = []
    if sanitized_query.get('device_drivers'):
        device_drivers = sanitized_query.get('device_drivers')
    if sanitized_query.get('npiv'):
        device_drivers = ['igb', 'ixgbe', 'be2net', 'mlx4_core', 'enic']
    if sanitized_query.get('sriov'):
        device_drivers = ['lpcf', 'qla2xxx']

    # Process required drivers
    if device_drivers:
        or_op = etree.SubElement(root, 'or')
        for driver_name in device_drivers:
            device = etree.SubElement(or_op, 'device')
            driver = etree.SubElement(device, 'driver')
            driver.set('op', '=')
            driver.set('value', driver_name)


def fill_host_requirements(host_requires: Element, sanitized_query: dict):
    """
    Fill host requires element for beaker job XML according to query
    """
    op_map = {
        '$eq': '=', '$gt': '>', '$lt': '<', '$lte': '<=', '$gte': '>=',
    }
    and_op = etree.SubElement(host_requires, 'and')

    # Prepare requirements according to parameters
    def add_requirement(key, op, value, is_extra=False):
        if is_extra:
            require = etree.SubElement(and_op, 'key_value')
            require.set("key", key)
        else:
            require = etree.SubElement(and_op, key)
        require.set("op", op)
        require.set("value", str(value))

    if sanitized_query.get('system-type', 'baremetal') == 'baremetal':
        add_requirement('hypervisor', '=', '')
    else:
        raise ValidateError('System type other that baremetal is not supported yet.')

    if sanitized_query.get('cpu-arch'):
        add_requirement('arch', '=', sanitized_query.get('cpu-arch'))

    for op, value in sanitized_query.get('memory-total_size', {}).items():
        add_requirement('memory', op_map[op], value)

    for flag in sanitized_query.get('cpu-flags', []):
        add_requirement('CPUFLAGS', '=', flag, is_extra=True)

    if sanitized_query.get('hvm'):
        add_requirement('HVM', '=', '1', is_extra=True)

    for op, value in sanitized_query.get('disk-total_size', {}).items():
        add_requirement("DISKSPACE", op_map[op], value, is_extra=True)

    for op, value in sanitized_query.get('disk-number', {}).items():
        add_requirement("NR_DISKS", op_map[op], value, is_extra=True)

    for op, value in sanitized_query.get('numa-node_number', {}).items():
        add_requirement("numa_node_count", op_map[op], value, is_extra=True)

    fill_cpu(and_op, sanitized_query)
    fill_devices(and_op, sanitized_query)


def add_reserve_task(recipe: Element, sanitized_query: dict):
    """
    Use a reserve task to reserve a machine.
    """
    task = etree.SubElement(recipe, 'task')
    task.set('name', '/distribution/dummy')
    task.set('role', 'STANDALONE')
    task_params = etree.SubElement(task, 'params')
    task_param = etree.SubElement(task_params, 'param')
    task_param.set('name', 'RSTRNT_DISABLED')
    task_param.set('value', '01_dmesg_check 10_avc_check')

    task = etree.SubElement(recipe, 'task')
    task.set('name', '/distribution/reservesys')
    task.set('role', 'STANDALONE')
    task_params = etree.SubElement(task, 'params')
    task_param = etree.SubElement(task_params, 'param')
    task_param.set('name', 'RSTRNT_DISABLED')
    task_param.set('value', '01_dmesg_check 10_avc_check')


def fill_boilerplate_recipe(recipe: Element, sanitized_query: dict):
    # Some default params
    recipe.set('whiteboard', DEFAULTS['job-whiteboard'])  # TODO
    recipe.set('role', 'None')

    # Some default params
    recipe.set('ks_meta', "method=nfs harness='restraint-rhts staf'")
    recipe.set('kernel_options', "")

    # Don't autopick
    autopick = etree.SubElement(recipe, 'autopick')
    autopick.set('random', 'false')

    # Don't autoreboot
    watchdog = etree.SubElement(recipe, 'watchdog')
    watchdog.set('panic', 'ignore')

    host_requires = etree.SubElement(recipe, 'hostRequires')

    ks_appends = etree.SubElement(recipe, 'ks_appends')
    repos = etree.SubElement(recipe, 'repos')
    distro_requires = etree.SubElement(recipe, 'distroRequires')
    packages = etree.SubElement(recipe, 'packages')

    fill_ks_appends(ks_appends, sanitized_query)
    fill_packages(packages, sanitized_query)
    fill_repos(repos, sanitized_query)
    fill_distro_requires(distro_requires, sanitized_query)

    fill_host_requirements(host_requires, sanitized_query)


def convert_query_to_beaker_xml(sanitized_query: dict):
    job = boilerplate_job(sanitized_query)

    # Use normal priority by default
    recipe_set = etree.SubElement(job, 'recipeSet')
    recipe_set.set('priority', 'Normal')

    # Always only one recipe
    recipe = etree.SubElement(recipe_set, 'recipe')

    fill_boilerplate_recipe(recipe, sanitized_query)

    add_reserve_task(recipe, sanitized_query)

    pretty_xml = minidom.parseString(etree.tostring(job)).toprettyxml(indent="  ")
    return pretty_xml
