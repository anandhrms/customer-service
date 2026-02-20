import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import router
from app.controllers import CloudDBController
from core.cache import Cache, CustomKeyMaker, RedisBackend
from core.config import config
from core.exceptions import CustomException
from core.factory import Factory
from core.fastapi.dependencies import Logging
from core.fastapi.middlewares import (
    AuthBackend,
    AuthenticationMiddleware,
    ProfilingMiddleware,
    ResponseLoggerMiddleware,
    SQLAlchemyMiddleware,
)
from core.library.logging import logger
from core.utils.firebase import CloudDBHandler, get_cloudDB_client

FIREBASE_INCIDENTS_COLLECTION = config.FIREBASE_INCIDENTS_COLLECTION
FIREBASE_CAMERA_COLLECTION = config.FIREBASE_CAMERA_COLLECTION
FIREBASE_CUSTOMER_DATA_COLLECTION = config.FIREBASE_CUSTOMER_DATA_COLLECTION

controller_factory = Factory()

cloudDB_client = get_cloudDB_client()
cloudDB_handler = CloudDBHandler(client=cloudDB_client)
cloudDB_controller = CloudDBController(cloudDB_handler=cloudDB_handler)


def start_incidents_listener(app: FastAPI):
    app.state.incident_listener_task = asyncio.create_task(
        cloudDB_controller.start_listener(
            FIREBASE_INCIDENTS_COLLECTION, asyncio.get_event_loop()
        )
    )
    logger.info("incidents listener started")
    app.state.incident_listener_context = True


def stop_incidents_listener(app: FastAPI):
    cloudDB_controller.stop_incident_listener()
    if app.state.incident_listener_task:
        app.state.incident_listener_task.cancel()
    logger.info("incidents listener stopped")
    app.state.incident_listener_context = False


def start_camera_listener(app: FastAPI):
    app.state.camera_listener_task = asyncio.create_task(
        cloudDB_controller.start_listener(
            FIREBASE_CAMERA_COLLECTION, asyncio.get_event_loop()
        )
    )
    logger.info("camera listener started")
    app.state.camera_listener_context = True


def stop_camera_listener(app: FastAPI):
    cloudDB_controller.stop_camera_listener()
    if app.state.camera_listener_task:
        app.state.camera_listener_task.cancel()
    logger.info("camera listener stopped")
    app.state.camera_listener_context = False


def start_customer_data_listener(app: FastAPI):
    app.state.customer_listener_task = asyncio.create_task(
        cloudDB_controller.start_listener(
            FIREBASE_CUSTOMER_DATA_COLLECTION, asyncio.get_event_loop()
        )
    )
    logger.info("customer data listener started")
    app.state.customer_data_listener_context = True


def stop_customer_data_listener(app: FastAPI):
    cloudDB_controller.stop_customer_data_listener()
    if app.state.customer_listener_task:
        app.state.customer_listener_task.cancel()
    logger.info("customer data listener stopped")
    app.state.customer_data_listener_context = False


def on_auth_error(request: Request, exc: Exception):
    status_code, error_code, message = 401, None, str(exc)
    if isinstance(exc, CustomException):
        status_code = int(exc.code)
        error_code = exc.error_code
        message = exc.message

    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "message": message},
    )


def init_routers(app_: FastAPI) -> None:
    app_.include_router(router)


def init_listeners(app_: FastAPI) -> None:
    @app_.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        return JSONResponse(
            status_code=exc.code,
            content={"error_code": exc.error_code, "message": exc.message},
        )

    @app_.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = []
        for err in exc.errors():
            if len(err["loc"]) > 1:
                errors.append({"field": err["loc"][1], "message": err["msg"]})

            else:
                errors.append({"message": err["msg"]})

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({"detail": errors}),
        )


def start_firebase_listeners(app: FastAPI):
    start_incidents_listener(app)
    start_camera_listener(app)
    start_customer_data_listener(app)


def stop_firebase_listeners(app: FastAPI):
    stop_incidents_listener(app)
    stop_camera_listener(app)
    stop_customer_data_listener(app)


async def start_listener_and_poll(app: FastAPI):
    while True:
        logger.info(
            "---------------------------------starting listener----------------------------------"
        )
        start_firebase_listeners(app)
        await asyncio.sleep(60)
        stop_firebase_listeners(app)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    task = asyncio.create_task(start_listener_and_poll(app))
    yield
    task.cancel()
    stop_firebase_listeners(app)


def make_middleware() -> list[Middleware]:
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(
            AuthenticationMiddleware,
            backend=AuthBackend(),
            on_error=on_auth_error,
        ),
        Middleware(SQLAlchemyMiddleware),
        Middleware(ResponseLoggerMiddleware),
    ]

    if config.PROFILING_ENABLED:
        middleware.append(Middleware(ProfilingMiddleware))

    return middleware


def init_cache() -> None:
    Cache.init(backend=RedisBackend(), key_maker=CustomKeyMaker())


def create_app() -> FastAPI:
    app_ = FastAPI(
        title="Visu Customer Service",
        description="Visu Customer Service by @Visu.ai",
        version="1.0.0",
        docs_url=None if config.ENVIRONMENT == "production" else "/docs",
        redoc_url=None if config.ENVIRONMENT == "production" else "/redoc",
        dependencies=[Depends(Logging)],
        middleware=make_middleware(),
        lifespan=app_lifespan if config.FIREBASE_LISTENER_ENABLED else None,
    )
    init_routers(app_=app_)
    init_listeners(app_=app_)
    init_cache()
    return app_


app = create_app()
