import logging

from aiohttp import web

from cuvette.utils import parse_query, parse_request_params, sanitize_query
from cuvette.utils import format_to_json, type_to_string
from cuvette.pipeline import Pipeline, Parameters
from cuvette.provisioners import Provisioners

logger = logging.getLogger(__name__)


def format_parameters(parameters: dict):
    return format_to_json(parameters, failover=type_to_string)


async def index(request):
    """
    Method: GET
    This is the view handler for the "/" url.
    Give a server running info
    """
    data = {
        'message': 'Cuvette working.',
        'version': '0.0.1'  # TODO
    }
    return web.json_response(data)


async def provisioners(request):
    """
    Method: GET
    Return info of provisioners
    """
    data = dict([
        (provisioner_name, provisioner.name)
        for provisioner_name, provisioner in Provisioners.items()
    ])
    return web.json_response(data)


async def parameters(request):
    """
    Method: GET
    Get all parameters of inspectors
    """
    data = format_parameters(Parameters)
    return web.json_response(data)


class MachineView(object):
    @staticmethod
    async def get(request):
        query_params = sanitize_query(
            parse_query(parse_request_params(request.query)),
            Parameters)
        machines = await Pipeline(request).query(query_params, nocount=True)
        return web.json_response([machine.to_json() for machine in machines])

    @staticmethod
    async def put(request):
        data = {
            'message': 'Not implemented, just return the request back',
            'request': str(request)
        }
        return web.json_response(data)

    @staticmethod
    async def post(request):
        data = {
            'message': 'Not implemented, just return the request back',
            'request': str(request)
        }
        return web.json_response(data)

    @staticmethod
    async def delete(request):
        query_params = sanitize_query(
            parse_query(parse_request_params(request.query)),
            Parameters)
        data = []
        machines = await Pipeline(request).query(query_params, nocount=True)
        for machine in machines:
            await machine.delete()
            data.append(machine.to_json())
        return web.json_response(data, status=200)

    @staticmethod
    async def request(request):
        """
        Method: GET
        A blocking machine request API, return until timeout (with 301) or there is a valid machine
        useful for clients that only wants a machine and nothing else.
        """
        if request.method == 'GET':
            query_params = parse_query(parse_request_params(request.query))
        elif request.method == 'POST':
            query_params = parse_query(await request.json())

        query_params = sanitize_query(query_params, Parameters)

        # Find / provision a ready machine and reserve it
        query_params.setdefault('status', 'ready')
        machines = await Pipeline(request).query(query_params)
        if not machines:
            machines = await Pipeline(request).provision(query_params, timeout=None)
        if machines:
            machines = await Pipeline(request).reserve(query_params)
        if machines and len(machines):
            return web.json_response([m.to_json() for m in machines])
        else:
            return web.json_response({
                'message': 'Failed to find or provision a machine'
            }, status=404)

    @staticmethod
    async def provision(request):
        """
        Method: POST
        Non blocking API to request to provision a machine
        """
        query_params = sanitize_query(parse_query(await request.json()), Parameters)

        if not await request['magic'].allow_provision(query_params):
            return web.json_response({'message': 'no avaliable'}, status=406)

        machines = await Pipeline(request).provision(query_params)
        return web.json_response([m.to_json() for m in machines])

    @staticmethod
    async def teardown(request):
        """
        Method: POST
        Non blocking API to request to force teardown a machine
        """
        query_params = sanitize_query(parse_query(await request.json()), Parameters)
        machines = await Pipeline(request).teardown(query_params)
        return web.json_response([m.to_json() for m in machines])

    @staticmethod
    async def release(request):
        """
        Method: POST
        Non blocking API to request to force release a machine
        """
        query_params = sanitize_query(parse_query(await request.json()), Parameters)
        machines = await Pipeline(request).release(query_params)
        return web.json_response([m.to_json() for m in machines])
