import logging
import socket
from aiohttp import web
from cuvette.pipeline import Pipeline

logger = logging.getLogger(__name__)


def resolve_peer_hostnames(request):
    """
    Return the request peer ip and reverse lookup it's hostname
    """
    peername = request.transport.get_extra_info('peername')
    if peername is not None:
        request_host, _port = peername
        host_candidates = {request_host}
        try:
            resolved_hosts = socket.gethostbyaddr(request_host)[0]
        except Exception:
            pass
        else:
            host_candidates.add(resolved_hosts)
        return list(host_candidates)
    return [None]


async def tear_me_down(request):
    """
    Method: GET
    Request this url with a host, then cuvette will tear down the host requesting if possible
    """
    host_candidates = resolve_peer_hostnames(request)

    machines = await Pipeline(request).teardown({
        'hostname': {
            '$in': host_candidates
        }
    })

    if machines and len(machines) > 0:
        return web.json_response(machines)
    else:
        return web.json_response({
            'message': "Can't find a machine with any following hostname '{}'".format(host_candidates)
        }, status=400)


async def release_me(request):
    """
    Method: GET
    Request this url with a host, then cuvette will release the host if possible
    """
    host_candidates = resolve_peer_hostnames(request)

    machines = await Pipeline(request).release({
        'hostname': {
            '$in': host_candidates
        }
    })

    if machines and len(machines) > 0:
        return web.json_response(machines)
    else:
        return web.json_response({
            'message': "Can't find a machine with any following hostname '{}'".format(host_candidates)
        }, status=400)


async def describ_me(request):
    """
    Method: GET
    Request this url with a host, then cuvette will return info about the host if possible
    """
    host_candidates = resolve_peer_hostnames(request)

    machines = await Pipeline(request).query({
        'hostname': {
            '$in': host_candidates
        }
    })

    if machines and len(machines) > 0:
        return web.json_response(machines)
    else:
        return web.json_response({
            'message': "Can't find a machine with any following hostname '{}'".format(host_candidates)
        }, status=400)
