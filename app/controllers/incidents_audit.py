from datetime import datetime

import pytz

from app.models import Incidents_Audit
from app.repositories import IncidentsAuditRepository
from app.schemas.requests import EditIncidentCommentsRequest
from core.controller import BaseController
from core.database import Propagation, Transactional
from core.exceptions import BadRequestException


class IncidentsAuditController(BaseController[Incidents_Audit]):
    def __init__(self, audit_repository: IncidentsAuditRepository):
        super().__init__(model=Incidents_Audit, repository=audit_repository)
        self.audit_repository = audit_repository

    async def get_audit_by_id(self, audit_id: int) -> Incidents_Audit:
        incident = await self.audit_repository.get_by_id(id=audit_id)

        if incident is None:
            raise BadRequestException(message="No such audit exists")

        return incident

    async def get_incident_audit(self, incident_id: int) -> list[Incidents_Audit]:
        return await self.audit_repository.get_incident_audit(incident_id=incident_id)

    async def edit_comments(
        self, user_id: int, edit_comments_request: EditIncidentCommentsRequest
    ):
        incident = await self.get_audit_by_id(edit_comments_request.id)

        incident.comments = edit_comments_request.comments
        incident.updated_by = user_id
        incident.edited = True
        incident.updated_at = datetime.now(pytz.utc)

        await self.audit_repository.session.commit()

        return incident

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(self, register_audit_request: dict) -> Incidents_Audit:
        return await self.audit_repository.create(register_audit_request)
