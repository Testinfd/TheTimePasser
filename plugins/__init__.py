from aiohttp import web
from .route import routes
from plugins.admin_dashboard import admin_routes, register_admin_routes

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    await register_admin_routes(web_app)
    return web_app
