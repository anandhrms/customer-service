from datetime import datetime

import pytz
from fastapi import APIRouter, Depends, HTTPException, Request

from app.controllers import ErrorLogsController, IncidentsController
from app.library.helpers import send_notification
from app.schemas.requests import SendNotificationRequest
from core.config import config
from core.exceptions import BadRequestException, NotFoundException
from core.factory import Factory
from core.library.logging import logger

notifications_router = APIRouter()

controller_factory = Factory()


@notifications_router.post(
    "/",
    tags=["Notifications"],
)
async def send_incident_notification(
    request: Request,
    send_notification_request: SendNotificationRequest,
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    error_logs_controller: ErrorLogsController = Depends(
        controller_factory.get_error_logs_controller
    ),
):
    try:
        incident_obj = await incidents_controller.get_by_id(
            send_notification_request.incident_id
        )

        if incident_obj is None:
            raise NotFoundException(
                f"Incident not found with this id: {send_notification_request.incident_id}"
            )

        if send_notification_request.notification_type.value == config.LIKELY_THEFT:
            template = config.LIKELY_THEFT_ALERT_TEMPLATE
            group = config.LIKELY_THEFT
            notification_group_type = config.NOTIFICATION_GROUP_TYPE_LIKELY_THEFT
            channel_id = config.NOTIFICATION_CHANNEL_LIKELY_THEFT_ALERT
            sound_name = config.NOTIFICATION_SOUND_LIKELY_THEFT_ALERT
            alert = False

        elif (
            send_notification_request.notification_type.value
            == config.PREVIOUSLY_BLACKLISTED
        ):
            template = config.PREVIOUSLY_BLACKLISTED_TEMPLATE
            group = config.PREVIOUSLY_BLACKLISTED
            notification_group_type = config.NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON
            channel_id = config.NOTIFICATION_CHANNEL_BLACKLIST_ALERT
            sound_name = config.NOTIFICATION_SOUND_BLACKLIST_ALERT
            alert = True

        elif send_notification_request.notification_type.value == config.SENSITIVE:
            template = config.SENSITIVE_ALERT_TEMPLATE
            group = config.SENSITIVE
            notification_group_type = config.NOTIFICATION_GROUP_TYPE_SENSITIVE_ALERT
            channel_id = config.NOTIFICATION_CHANNEL_SENSITIVE_ALERT
            sound_name = config.NOTIFICATION_SOUND_SENSITIVE_ALERT
            alert = False

        elif (
            send_notification_request.notification_type.value == config.CAMERA_INCIDENTS
        ):
            template = config.CAMERA_DOWN_TEMPLATE
            group = config.CAMERA_INCIDENTS
            notification_group_type = config.NOTIFICATION_GROUP_TYPE_CAMERA_DOWN
            channel_id = None
            sound_name = None
            alert = False

        else:
            raise BadRequestException(
                f"Invalid notification_type: {send_notification_request.notification_type}"
            )

        await send_notification(
            branch_id=incident_obj.branch_id,
            template=template,
            incident=incident_obj,
            group=group,
            notification_group_type=notification_group_type,
            alert=alert,
            channel_id=channel_id,
            sound_name=sound_name,
        )

        return {"status": "success", "message": "Notification sent successfully"}

    except NotFoundException as e:
        await error_logs_controller.register(
            {
                "incident_id": send_notification_request.incident_id,
                "error_msg": str(e),
                "created_at": datetime.now(pytz.utc),
            }
        )
        raise HTTPException(status_code=e.code, detail=e.message)

    except BadRequestException as e:
        await error_logs_controller.register(
            {
                "incident_id": send_notification_request.incident_id,
                "error_msg": str(e),
                "created_at": datetime.now(pytz.utc),
            }
        )
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"{request.method} {request.url} : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
