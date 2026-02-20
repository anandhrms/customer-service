from datetime import datetime

import pytz

from app.models import Customers_Audit
from app.repositories import CustomersAuditRepository
from app.schemas.requests import EditCustomersCommentsRequest
from core.controller import BaseController
from core.database import Propagation, Transactional
from core.exceptions import BadRequestException


class CustomersAuditController(BaseController[Customers_Audit]):
    def __init__(self, audit_repository: CustomersAuditRepository):
        super().__init__(model=Customers_Audit, repository=audit_repository)
        self.audit_repository = audit_repository

    async def get_audit_by_id(self, audit_id: int) -> Customers_Audit:
        incident = await self.audit_repository.get_by_id(id=audit_id)

        if incident is None:
            raise BadRequestException(message="No such audit exists")

        return incident

    async def get_customer_audit(self, customer_id: int) -> list[Customers_Audit]:
        return await self.audit_repository.get_customer_audit(customer_id=customer_id)

    async def edit_comments(
        self, user_id: int, edit_comments_request: EditCustomersCommentsRequest
    ):
        audit_obj = await self.get_audit_by_id(edit_comments_request.id)

        audit_obj.comments = edit_comments_request.comments
        audit_obj.updated_by = user_id
        audit_obj.edited = True
        audit_obj.updated_at = datetime.now(pytz.utc)

        await self.audit_repository.session.commit()

        return audit_obj

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(self, register_audit_request: dict) -> Customers_Audit:
        return await self.audit_repository.create(register_audit_request)
