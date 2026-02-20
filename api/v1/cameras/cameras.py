from fastapi import APIRouter, Depends, HTTPException

from app.controllers import CloudDBController
from app.schemas.requests import CreateCameraIncidentsRequest
from core.exceptions import ForbiddenException
from core.factory import Factory
from core.fastapi.dependencies import AuthenticationRequired
from core.library.logging import logger

controller_factory = Factory()

camera_router = APIRouter()


@camera_router.post(
    "/incidents",
    tags=["Cameras"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def create_camera_incident_test(
    create_camera_incident_request: CreateCameraIncidentsRequest,
    firestore_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        return firestore_controller.publish_camera_incident(
            create_camera_incident_request.model_dump()
        )

    except ForbiddenException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"POST /incidents/ : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
