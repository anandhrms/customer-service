import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from app.controllers import CloudDBController
from core.config import config
from core.factory import Factory
from core.fastapi.dependencies import SuperAdminPermissionRequired
from core.library import logger

firestore_router = APIRouter()

controller_factory = Factory()

FIREBASE_INCIDENTS_COLLECTION = config.FIREBASE_INCIDENTS_COLLECTION
FIREBASE_CAMERA_COLLECTION = config.FIREBASE_CAMERA_COLLECTION
FIREBASE_CUSTOMER_DATA_COLLECTION = config.FIREBASE_CUSTOMER_DATA_COLLECTION


@firestore_router.get(
    "/incidents/start-listener",
    tags=["Firebase"],
    dependencies=[Depends(SuperAdminPermissionRequired)],
    include_in_schema=False,
)
async def start_incidents_listener(
    request: Request,
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        if not (
            hasattr(request.app.state, "incident_listener_context")
            and request.app.state.incident_listener_context
        ):
            request.app.state.incident_listener_task = asyncio.create_task(
                cloudDB_controller.start_listener(
                    FIREBASE_INCIDENTS_COLLECTION, asyncio.get_event_loop()
                )
            )
            request.app.state.incident_listener_context = True
            return {"status": "Listener started"}

        else:
            return {"status": "Listener is already running"}

    except Exception as e:
        logger.error(f"GET /firebase/incidents/start-listener : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@firestore_router.get(
    "/incidents/stop-listener",
    tags=["Firebase"],
    dependencies=[Depends(SuperAdminPermissionRequired)],
    include_in_schema=False,
)
async def stop_incidents_listener(
    request: Request,
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        if (
            hasattr(request.app.state, "incident_listener_context")
            and request.app.state.incident_listener_context
        ):
            response = cloudDB_controller.stop_incident_listener()

            if (
                hasattr(request.app.state, "incident_listener_task")
                and request.app.state.incident_listener_task
            ):
                request.app.state.incident_listener_task.cancel()

            request.app.state.incident_listener_context = False
            return response

        else:
            return {"status": "No active incidents listener"}

    except Exception as e:
        logger.error(f"GET /firebase/incidents/stop-listener : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@firestore_router.get(
    "/camera/start-listener",
    tags=["Firebase"],
    dependencies=[Depends(SuperAdminPermissionRequired)],
    include_in_schema=False,
)
async def start_camera_listener(
    request: Request,
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        if not (
            hasattr(request.app.state, "camera_listener_context")
            and request.app.state.camera_listener_context
        ):
            request.app.state.camera_listener_task = asyncio.create_task(
                cloudDB_controller.start_listener(
                    FIREBASE_CAMERA_COLLECTION, asyncio.get_event_loop()
                )
            )
            request.app.state.camera_listener_context = True
            return {"status": "Camera Listener started"}

        else:
            return {"status": "Listener is already running"}

    except Exception as e:
        logger.error(f"GET /firebase/camera/start-listener : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@firestore_router.get(
    "/camera/stop-listener",
    tags=["Firebase"],
    dependencies=[Depends(SuperAdminPermissionRequired)],
    include_in_schema=False,
)
async def stop_camera_listener(
    request: Request,
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        if (
            hasattr(request.app.state, "camera_listener_context")
            and request.app.state.camera_listener_context
        ):
            response = cloudDB_controller.stop_camera_listener()

            if (
                hasattr(request.app.state, "camera_listener_task")
                and request.app.state.camera_listener_task
            ):
                request.app.state.camera_listener_task.cancel()

            request.app.state.camera_listener_context = False
            return response

        else:
            return {"status": "No active camera listener"}

    except Exception as e:
        logger.error(f"GET /firebase/camera/stop-listener : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@firestore_router.get(
    "/customer-data/start-listener",
    tags=["Firebase"],
    dependencies=[Depends(SuperAdminPermissionRequired)],
    include_in_schema=False,
)
async def start_customer_data_listener(
    request: Request,
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        if not (
            hasattr(request.app.state, "customer_data_listener_context")
            and request.app.state.customer_data_listener_context
        ):
            request.app.state.customer_listener_task = asyncio.create_task(
                cloudDB_controller.start_listener(
                    FIREBASE_CUSTOMER_DATA_COLLECTION, asyncio.get_event_loop()
                )
            )
            request.app.state.customer_data_listener_context = True
            return {"status": "Customer data Listener started"}

        else:
            return {"status": "Listener is already running"}

    except Exception as e:
        logger.error(f"GET /firebase/customer-data/start-listener : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@firestore_router.get(
    "/customer-data/stop-listener",
    tags=["Firebase"],
    dependencies=[Depends(SuperAdminPermissionRequired)],
    include_in_schema=False,
)
async def stop_customer_data_listener(
    request: Request,
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        if (
            hasattr(request.app.state, "customer_data_listener_context")
            and request.app.state.customer_data_listener_context
        ):
            response = cloudDB_controller.stop_customer_data_listener()

            if (
                hasattr(request.app.state, "customer_listener_task")
                and request.app.state.customer_listener_task
            ):
                request.app.state.customer_listener_task.cancel()

            request.app.state.customer_data_listener_context = False
            return response

        else:
            return {"status": "No active incidents listener"}

    except Exception as e:
        logger.error(f"GET /firebase/customer-data/stop-listener : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
