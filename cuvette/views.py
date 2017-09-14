from aiohttp import web
from cuvette.pipeline import Pipeline
from cuvette.inspectors import Parameters


async def index(request):
    """
    This is the view handler for the "/" url.

    :param request: the request object see http://aiohttp.readthedocs.io/en/stable/web_reference.html#request
    :return: aiohttp.web.Response object
    """
    # with the base web.Response type we have to manually set the content type, otherwise text/plain will be used.
    data = {
        'text': 'Hello World!'
    }
    return web.json_response(data)


async def parameters(request):
    """
    This is the view handler for the "/" url.

    :param request: the request object see http://aiohttp.readthedocs.io/en/stable/web_reference.html#request
    :return: aiohttp.web.Response object
    """
    # with the base web.Response type we have to manually set the content type, otherwise text/plain will be used.
    data = Parameters
    return web.json_response(data)


class MachineView(object):
    @staticmethod
    async def get(request):
        machines = await Pipeline(request).query(request.query)
        if not machines:
            machines = await Pipeline(request).provision(request.query)
        if machines:
            return web.json_response(machines)
        else:
            return web.json_response({
                'message': 'Failed to find or provision a machine'
            })

    @staticmethod
    async def post(request):
        data = {
            'message': 'Not implemented, just return the request back',
            'request': str(request)
        }
        return web.json_response(data)
