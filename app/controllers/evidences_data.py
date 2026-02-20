from app.models.incidents import Evidence
from app.repositories import EvidenceDataRepository
from core.controller.base import BaseController
from core.database import Propagation, Transactional


class EvidenceDataController(BaseController[Evidence]):
    def __init__(self, evidence_data_repository: EvidenceDataRepository):
        super().__init__(Evidence, evidence_data_repository)
        self.evidence_data_repository = evidence_data_repository

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(self, create_evidence_data_request: dict) -> Evidence:
        return await self.evidence_data_repository.create(create_evidence_data_request)

    async def get_by_id(self, evidence_id: int) -> Evidence | None:
        return await self.evidence_data_repository.get_by_id(evidence_id)

    async def get_by_incident_id(self, incident_id: int) -> list[Evidence]:
        return await self.evidence_data_repository.get_by_incident_id(incident_id)

    async def evidence_update(
        self, evidence_id: int, update_data: dict
    ) -> Evidence | None:
        return await self.evidence_data_repository.evidence_update(
            evidence_id, update_data
        )
