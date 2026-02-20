from enum import Enum

from pydantic import BaseModel

from core.config import config


class NotificationType(Enum):
    CAMERA_INCIDENTS = config.CAMERA_INCIDENTS
    SENSITIVE = config.SENSITIVE
    LIKELY_THEFT = config.LIKELY_THEFT
    PREVIOUSLY_BLACKLISTED = config.PREVIOUSLY_BLACKLISTED


class SendNotificationRequest(BaseModel):
    incident_id: int
    notification_type: NotificationType
