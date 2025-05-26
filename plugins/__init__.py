from aiohttp import web
from .route import routes, setup_routes

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app = setup_routes(web_app)
    return web_app
