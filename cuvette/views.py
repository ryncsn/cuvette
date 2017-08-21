from aiohttp import web
from cuvette.pipeline import Pipeline


async def index(request):
    """
    This is the view handler for the "/" url.

    **Note: returning html without a template engine like jinja2 is ugly, no way around that.**

    :param request: the request object see http://aiohttp.readthedocs.io/en/stable/web_reference.html#request
    :return: aiohttp.web.Response object
    """
    # with the base web.Response type we have to manually set the content type, otherwise text/plain will be used.
    data = {
        'text': 'Hello World!'
    }
    return web.json_response(data)


class MachineView(object):
    @staticmethod
    async def get(request):
        machines = await Pipeline(request).query(request.query)
        if not machines:
            machines = await Pipeline(request).provision(request.query)
        if machines:
            return web.json_response(machines)

    @staticmethod
    async def post(request):
        data = {
            'request': str(request)
        }
        return web.json_response(data)
