import logging

from aiohttp import web

from cuvette.utils import parse_query, parse_request_params
from cuvette.pipeline import Pipeline
from cuvette.inspectors import Parameters
from cuvette.provisioners import Provisioners

logger = logging.getLogger(__name__)


async def index(request):
    """
    Method: GET
    This is the view handler for the "/" url.
    Give a server running info
    """
    # with the base web.Response type we have to manually set the content type, otherwise text/plain will be used.
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
    # with the base web.Response type we have to manually set the content type, otherwise text/plain will be used.
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
    # with the base web.Response type we have to manually set the content type, otherwise text/plain will be used.
    data = Parameters
    return web.json_response(data)


class MachineView(object):
    @staticmethod
    async def get(request):
        query_params = parse_query(parse_request_params(request.query))

        # Magic deal with the problem that browser keep sending request
        # Result in tons of request job
        machines = await Pipeline(request).query(query_params)
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
        query_params = parse_query(parse_request_params(request.query))
        data = []
        machines = await Pipeline(request).query(query_params)
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

        machines = await request['magic'].pre_query(query_params)
        if not machines:
            machines = await Pipeline(request).query(query_params)
        if not machines:
            machines = await Pipeline(request).provision(query_params, timeout=None)
        if machines:
            return web.json_response(machines)
        else:
            return web.json_response({
                'message': 'Failed to find or provision a machine'
            }, 404)

    @staticmethod
    async def provision(request):
        """
        Method: POST
        Non blocking API to request to provision a machine
        """
        # with the base web.Response type we have to manually set the content type, otherwise text/plain will be used.
        query_params = parse_query(await request.json())

        if not await request['magic'].allow_provision(query_params):
            return web.json_response({'message': 'no avaliable'}, status=406)

        machines = await Pipeline(request).provision(query_params)
        return web.json_response(machines)

    @staticmethod
    async def teardown(request):
        """
        Method: POST
        Non blocking API to request to force teardown a machine
        """
        # with the base web.Response type we have to manually set the content type, otherwise text/plain will be used.
        query_params = parse_query(await request.json())
        machine = await Pipeline(request).teardown(query_params)
        return web.json_response(machine)
