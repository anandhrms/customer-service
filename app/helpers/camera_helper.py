from datetime import datetime

from app.library.entity_service import entity
from core.config import config
from core.library.logging import logger

from .entity_helper import get_company_branch_camera_id
from .notification_helper import send_notification

CAMERA_UP_TEMPLATE = config.CAMERA_UP_TEMPLATE
CAMERA_DOWN_TEMPLATE = config.CAMERA_DOWN_TEMPLATE
CAMERA_INCIDENTS = config.CAMERA_INCIDENTS

NOTIFICATION_GROUP_TYPE_CAMERA_DOWN = config.NOTIFICATION_GROUP_TYPE_CAMERA_DOWN


async def add_camera_incident(data: dict):
    company_branch_camera_response = await get_company_branch_camera_id(
        company_uuid=data.get("com_id"),
        branch_uuid=data.get("st_id"),
        camera_uuid=data.get("cam_id"),
    )

    if company_branch_camera_response is None:
        logger.error("Error in finding company or branch or camera")
        return

    _, branch_id, camera_id = company_branch_camera_response

    status = data.get("status")

    create_camera_incident_request = {
        "camera_id": camera_id,
        "camera_incident_id": data.get("cam_inci_id"),
        "comments": data.get("comments"),
        "status": status,
        "branch_id": branch_id,
    }

    camera_incident_time = data.get("cam_inci_time")

    camera_incident_time = datetime.strptime(
        camera_incident_time, "%B %d, %Y %H:%M:%S"
    ).isoformat()

    if status == 0:
        await send_notification(
            branch_id=branch_id,
            template=CAMERA_DOWN_TEMPLATE,
            incident=None,
            group=CAMERA_INCIDENTS,
            notification_group_type=NOTIFICATION_GROUP_TYPE_CAMERA_DOWN,
        )

    # elif status == 1:
    #     await send_notification(
    #         branch_id=branch_id,
    #         template=CAMERA_UP_TEMPLATE,
    #         incident_id=None,
    #         group=CAMERA_INCIDENTS,
    #         notification_group_type=NOTIFICATION_GROUP_TYPE_CAMERA_DOWN,
    #     )

    create_camera_incident_request["camera_incident_time"] = camera_incident_time

    await entity.create_camera_incidents(create_camera_incident_request)
