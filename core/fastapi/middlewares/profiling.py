from pyinstrument import Profiler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.library.logging import logger


class ProfilingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        profiler = Profiler()
        profiler.start()
        response = await call_next(request)
        profiler.stop()
        logger.info(f"{request.url} {profiler.output_text(unicode=True)}")
        return response
