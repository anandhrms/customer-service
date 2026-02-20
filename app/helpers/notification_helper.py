import time
from typing import Optional, Tuple

from app.library.entity_service import entity
from app.models import Incidents
from core.config import config
from core.library.logging import logger
from core.utils.firebase import get_firebase_handler


def get_notification_content(template: str) -> Tuple[Optional[str], str]:
    title: Optional[str] = None
    content = ""

    if template == config.SENSITIVE_ALERT_TEMPLATE:
        title = "Alert"
        content = "A alert has been triggered in your store. Please review and take immediate action."

    elif template == config.PREVIOUSLY_BLACKLISTED_TEMPLATE:
        # no custom title -> fallback to template later
        content = (
            "A previously watchlisted customer has been detected in your store. "
            "Please verify their presence and take immediate action."
        )

    elif template == config.LIKELY_THEFT_ALERT_TEMPLATE:
        title = "Alert"
        content = "A alert has been triggered in your store. Please review and take immediate action."

    elif template == config.CAMERA_DOWN_TEMPLATE:
        content = "We have observed that your camera is down"

    return title, content


def get_analytics_label(group: str) -> str:
    if group == config.PREVIOUSLY_BLACKLISTED:
        analytics_label = "customer_was_on_watchlist"
    elif group == config.SENSITIVE:
        analytics_label = "customer_gesture_alert"
    elif group == config.LIKELY_THEFT:
        analytics_label = "customer_likely_theft"
    elif group == config.CAMERA_INCIDENTS:
        analytics_label = "customer_camera_down"
    else:
        analytics_label = "customer_unknown_label"

    return analytics_label


async def send_notification(
    branch_id,
    template,
    incident: Incidents | None,
    group: int,
    notification_group_type: str,
    notification_type: str | None = None,
    except_user_ids: list[int] | None = None,
    alert: bool = False,
    channel_id: str | None = None,
    sound_name: str | None = None,
):
    start = time.time()
    tokens = await entity.get_fcm_token(
        branch_id=branch_id,
        except_user_ids=except_user_ids,
        notification_group_type=notification_group_type,
        notification_type=notification_type,
    )
    logger.info(f"time taken for getting FCM tokens is {time.time() - start}")

    firebase_handler = get_firebase_handler()
    analytics_label = get_analytics_label(group)
    title, notification_msg = get_notification_content(template)

    data = {"title": title or template, "body": notification_msg}

    if incident is None:
        notification_img = None
    elif incident.incident_type == Incidents.IncidentType.CUSTOMER_THEFT:
        notification_img = incident.thumbnail_url
    elif incident.incident_type == Incidents.IncidentType.PREVIOUSLY_BLACKLISTED:
        notification_img = incident.photo_url

    start = time.time()
    await firebase_handler.send_fcm_notification(
        data=data,
        tokens=tokens,
        incident_id=incident.id if incident else None,
        notification_img=notification_img,
        analytics_label=analytics_label,
        alert=alert,
        channel_id=channel_id,
        sound_name=sound_name,
    )
    logger.info(
        f"total time taken for sending notification for incident_id {incident.id} is {time.time() - start}"
    )

    start = time.time()
    await entity.create_notification(
        branch_id=branch_id,
        template=template,
        group=group,
        incident_id=incident.id,
        notification_group_type=notification_group_type,
    )
    logger.info(f"time taken for creating notification is {time.time() - start}")
