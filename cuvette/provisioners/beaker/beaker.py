import re
import asyncio
import logging
import datetime

from asyncio.subprocess import PIPE, STDOUT
from cuvette.settings import Settings

from lxml import etree
from .convertor import convert_query_to_beaker_xml


logger = logging.getLogger(__name__)


BEAKER_URL = Settings.BEAKER_URL


async def bkr_command(*args, input=None):
    p = await asyncio.create_subprocess_exec(
        *(['bkr'] + list(args)),
        stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    stdout, stderr = await p.communicate(input=bytes(input, 'utf8') if input else None)
    if stderr:
        logger.error("Failed calling bkr with error:", stderr)
    return stdout.decode('utf8')


async def cancel_beaker_job(job_id: str):
    await bkr_command('job-cancel', job_id)


def query_to_xml(sanitized_query: dict) -> str:
    """
    Convert a query to XML that could be recognized by beaker
    """
    return convert_query_to_beaker_xml(sanitized_query)


async def execute_beaker_job(job_xml: str):
    """
    Submit a job to beaker and wait for it to pass
    """
    success = False
    attempt = 0
    logger.info("Submitting with beaker Job XML:\n%s", job_xml)
    while not success:
        task_id_output = await bkr_command('job-submit', input=job_xml)
        try:
            # There should be only one job
            job_id, = re.match("Submitted: \['(J:[0-9]+)'(?:,)?\]", task_id_output).groups()
            task_url = "{}/jobs/{}".format(BEAKER_URL, job_id[2:])
        except (ValueError, TypeError, AttributeError):
            logger.error('Expecting one job id, got: %s', task_id_output)
            raise RuntimeError('bkr job-submit command failure {}'.format(task_id_output))
        else:
            logger.info("Submitted beaker job %s", task_url)
        try:
            while True:
                await asyncio.sleep(55)
                attempt += 1
                logger.info("Checking status of job %s (attempt %s)", task_url, attempt)
                for _ in range(5):  # Try to fetch for multiple times
                    try:
                        active_job_xml_str = await bkr_command('job-results', job_id)
                        active_job_xml = etree.fromstring(active_job_xml_str)
                        break
                    except Exception:
                        await asyncio.sleep(10)
                recipes = list(map(lambda x: dict(x.attrib), active_job_xml.xpath('//recipe')))
                if not recipes:
                    logger.error("Can't find valid recipe: {}".format(active_job_xml_str))
                    raise RuntimeError('bkr job-results command failure {}'.format(active_job_xml_str))
                for recipe in recipes:
                    logger.info("Recipe %s: (system = %s) (status = %s) (result = %s)",
                                recipe['id'], recipe.get('system', 'queuing'),
                                recipe['status'], recipe['result'])
                if any(info['result'] in ['Warn', 'Fail', 'Panic'] for info in recipes):
                    logger.info("Beaker job %s failed. Resubmit job.", task_url)
                    break
                elif any(info['status'] in ['Aborted'] for info in recipes):
                    logger.info("Beaker job %s finished unexpectedly. " "Resubmit job.", task_url)
                    break
                elif all(info['status'] == 'Running' and info['result'] == 'Pass' for info in recipes):
                    logger.info("Beaker job %s was successfully finished", task_url)
                    success = True
                    return job_id, recipes
        finally:
            if not success:
                logger.error("Provisioning aborted abnormally. Cancellling beaker job %s", task_url)
                await cancel_beaker_job(job_id)


async def parse_machine_info(recipe: str):
    """
    Parse recipe xml to get machine info
    """
    DEFAULT_LIFE_SPAN = 86400

    NS_INV = 'https://fedorahosted.org/beaker/rdfschema/inventory#'
    NS_INV = '{%s}' % NS_INV

    NS_RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    NS_RDF = '{%s}' % NS_RDF

    ret = {}

    system_tag_map = {
        '{}cpuSpeed'.format(NS_INV): {
            'name': 'cpu-speed',
            'type': float,
        },
        '{}cpuVendor'.format(NS_INV): {
            'name': 'cpu-vendor',
            'type': str,
        },
        '{}cpuFamilyId'.format(NS_INV): {
            'name': 'cpu-family',
            'type': int,
        },
        '{}cpuModelId'.format(NS_INV): {
            'name': 'cpu-model',
            'type': int,
        },
        '{}cpuCount'.format(NS_INV): {
            'name': 'cpu-core_number',
            'type': int,
        },
        '{}cpuSocketCount'.format(NS_INV): {
            'name': 'cpu-socket_number',
            'type': int,
        },
        '{}cpuFlag'.format(NS_INV): {
            'name': 'cpu-flags',
            'type': list,
        },
        '{}cpuStepping'.format(NS_INV): {
            'name': 'cpu-stepping',
            'type': list,
        },
        '{}cpuModelName'.format(NS_INV): {
            'name': 'cpu-model_name',
            'type': str,
        },
        '{}numaNodes'.format(NS_INV): {
            'name': 'numa-node_number',
            'type': int,
        },
        '{}model'.format(NS_INV): {
            'name': 'system-model',
            'type': str,
        },
        '{}vendor'.format(NS_INV): {
            'name': 'system-vendor',
            'type': str,
        },
        '{}memory'.format(NS_INV): {
            'name': 'memory-total_size',
            'type': int,
        },
        '{}macAddress'.format(NS_INV): {
            'name': 'net-mac_address',
            'type': str,
        },
        # TODO
        # '{}hasDevice'.format(NS_INV): {
        # },
    }

    system_tag_map.update(Settings.EXTRA_BEAKER_NS_MAP)

    ret['lifespan'] = DEFAULT_LIFE_SPAN
    ret['start_time'] = datetime.datetime.strptime(recipe['start_time'], '%Y-%m-%d %H:%M:%S')
    ret['cpu-arch'] = recipe['arch']
    ret['beaker-distro'] = recipe['distro']
    ret['beaker-distro_family'] = recipe['family']
    ret['beaker-distro_variant'] = recipe['variant']
    ret['hostname'] = recipe['system']

    for _ in range(5):  # retry 5 times
        try:
            recipe_detail_xml_str = await bkr_command('system-details', recipe['system'])
            logger.info(recipe_detail_xml_str)
            recipe_detail = etree.fromstring(bytes(recipe_detail_xml_str, 'utf8'))
            break
        except Exception as error:
            logger.exception("Get error while processing recipe result")
            await asyncio.sleep(10)

    system = recipe_detail.find('{}System'.format(NS_INV))
    controlled_by = system.find('{}controlledBy'.format(NS_INV))
    lab_controller = controlled_by.find('{}LabController'.format(NS_INV))
    lab_controller_url = lab_controller.get('{}about'.format(NS_RDF))
    lab_controller = lab_controller_url.split('/')[-1].split('#')[0]

    ret['lab_controller'] = lab_controller

    for tag, meta in system_tag_map.items():
        key = meta['name']
        type_ = meta['type']
        values = system.findall(tag)
        if not values:
            continue
        if type_ == list:
            ret[key] = [str(v.text) for v in values]
        else:
            if len(values) > 1:
                logger.error('Expectin only one element for %s, got multiple.', tag)
            ret[key] = type_(values[0].text)

    system_type = ret.get('system-type')
    if not system_type or system_type == 'None':
        ret['system-type'] = 'baremetal'

    return ret
