from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    user_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None


class AuditResponse(BaseModel):
    audit_id: int
    action_type: int
    updated_at: datetime
    updated_by: UserResponse
    comments: str | None
    status: int
    edited: bool

    class Config:
        from_attributes = True


class SuspiciousIncidentsResponse(BaseModel):
    incident_id: int
    video_url: str
    photo_url: str
    thumbnail_url: str | None
    is_valid: int | None
    incident_time: datetime
    comments: str | None = None


class IncidentResponse(BaseModel):
    id: int
    uuid: str | None = None
    branch_id: int
    branch_name: str | None = None
    incident_type: int
    incident_time: datetime
    duration: str | None = None
    photo_url: str
    video_url: str
    thumbnail_url: str | None
    suspicious_incidents: list[SuspiciousIncidentsResponse]
    name: str
    status: int
    comments: str | None = None
    is_blacklisted: bool
    analyst_blacklisted: bool | None = None
    is_valid: int | None
    blacklisted_on: datetime | None = None
    prev_incident_id: int | None = None
    match_score: float | None = None
    audit: list[AuditResponse] | None
    prev_photo_url: str | None = None
    prev_incident_time: datetime | None = None
    prev_duration: str | None = None
    response: str | None = None


class BranchIncidentsCountResponse(BaseModel):
    id: int
    branch_name: str | None
    likely_theft_count: int
    sensitive_theft_count: int
    blacklist_count: int
    camera_status: int | None = 1
    camera_down_content: str | None = None
    hardware_status: int | None = 1
    hardware_down_content: str | None = None
    hardware_troubleshoot: bool | None = None
    hardware_troubleshoot_url: str | None = None


class BlacklistIncidentResponse(BaseModel):
    id: int = 1
    uuid: str | None = None
    branch_id: int
    branch_name: str | None = None
    incident_type: int
    incident_time: datetime
    duration: str | None = None
    photo_url: str
    video_url: str
    thumbnail_url: str | None
    suspicious_incidents: list[SuspiciousIncidentsResponse]
    name: str
    status: int
    comments: str | None = None
    blacklisted_on: datetime
    prev_incident_id: int | None = None
    audit: list[AuditResponse] | None
    is_blacklisted: bool
    analyst_blacklisted: bool | None = None
    is_valid: int | None
    match_score: float | None = None
    prev_incident_time: datetime | None = None
    prev_photo_url: str | None = None
    prev_duration: str | None = None


class BaseUpdateResponse(BaseModel):
    status: str = "success"


class UpdateIncidentResponse(BaseUpdateResponse):
    message: str = " The incident is updated successfully"


class CreateIncidentResponse(BaseUpdateResponse):
    inci_id: str | None = None
    message: str = " The incident is created successfully"


class RemoveBlacklistResponse(BaseUpdateResponse):
    message: str = "Removed from blacklist successfully"


class AddToBlacklistResponse(BaseUpdateResponse):
    message: str = "Blacklisted successfully"
