from sqlalchemy import update

from app.models.incidents import Evidence
from core.repository import BaseRepository


class EvidenceDataRepository(BaseRepository[Evidence]):
    async def get_by_id(
        self, id: int, join_: set[str] | None = None
    ) -> Evidence | None:
        """
        Get Incidents_Audit by id.
        :param int: Incidents_Audit id.
        :param join_: Join relations.
        :return: Incidents_Audit.
        """

        query = await self._query(join_)
        query = query.filter(Evidence.id == id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)

    async def get_by_incident_id(
        self, incident_id: int, join_: set[str] | None = None
    ) -> list[Evidence]:
        """
        Get Evidences by incident_id.
        :param incident_id: Incident id.
        :param join_: Join relations.
        :return: List of Evidences.
        """

        query = await self._query(join_)
        query = query.filter(Evidence.incident_id == incident_id)
        return await self._all_unique(query)

    async def evidence_update(
        self, evidence_id: int, update_data: dict
    ) -> Evidence | None:
        """
        Update a single Evidence record.
        :param update_data: Data to update.
        :return: Updated Evidence or None if no record found.
        """
        query = (
            update(Evidence)
            .where(Evidence.id == evidence_id)
            .values(**update_data)
            .returning(Evidence)
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.scalar_one_or_none()
