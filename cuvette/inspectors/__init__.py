"""
Inspectors
"""
import os
import glob
import logging
import asyncssh

from cuvette.utils import find_all_sub_module, load_all_sub_module

logger = logging.getLogger(__name__)

__all__ = find_all_sub_module(__file__, exclude=['base'])
Inspectors = dict((k, v.Inspector()) for k, v in load_all_sub_module(__name__).items())


SSH_USER = 'root'
SSH_PASSWORD = 'redhat'


def load_all_keys():
    key_files = glob.glob(
        os.path.join(os.path.dirname(__file__), '..') + "/keys/*")
    user_key_files = [os.path.expanduser(file_) for file_ in [
        '~/.ssh/id_ed25519',
        '~/.ssh/id_ecdsa',
        '~/.ssh/id_rsa',
        '~/.ssh/id_dsa'
    ]]
    keys = []
    for file_ in key_files + user_key_files:
        try:
            keys.append(asyncssh.read_private_key(file_))
        except Exception:
            pass
    return keys


def get_all_parameters():
    """
    Return a dictionary descripting the parameters provided by all inspectors
    """
    ret = {}
    for inspector in Inspectors.values():
        for key, value in inspector.PARAMETERS.items():
            if key in ret.keys():
                logger.warn('Found duplicated parameter %s', key)
            ret[key] = value
            ret[key].setdefault('source', []).append(str(inspector))
    return ret


Parameters = get_all_parameters()


async def perform_check(machine):
    try:
        async with asyncssh.connect(machine['hostname'],
                                    known_hosts=None,
                                    username=SSH_USER,
                                    password=SSH_PASSWORD,
                                    client_keys=load_all_keys()
                                    ) as conn:
            # TODO: Disabled host key checking
            # TODO: Accept password
            # TODO: Accept username
            for ins in Inspectors.values():
                await ins.inspect(machine, conn)
    except (OSError, asyncssh.Error) as error:
        logger.exception('Failed inspecting machine %s with exception:', machine)
        await machine.fail()
