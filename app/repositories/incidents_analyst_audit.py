from app.models import Incidents_Analyst_Audit
from core.repository import BaseRepository


class IncidentsAnalystAuditRepository(BaseRepository[Incidents_Analyst_Audit]):
    """
    Incidents_Analyst_Audit repository provides all the database operations for the Incidents_Analyst_Audit model.
    """

    async def get_by_id(
        self, id: int, join_: set[str] | None = None
    ) -> Incidents_Analyst_Audit | None:
        """
        Get Incidents_Analyst_Audit by id.
        :param int: Incidents_Analyst_Audit id.
        :param join_: Join relations.
        :return: Incidents_Analyst_Audit.
        """
        query = await self._query(join_)
        query = query.filter(Incidents_Analyst_Audit.id == id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)

    async def get_incident_audit(self, incident_id: int, join_: set[str] | None = None):
        query = await self._query(join_)
        query = query.filter(
            Incidents_Analyst_Audit.incident_id == incident_id,
        )
        query = query.order_by(Incidents_Analyst_Audit.created_at.desc())

        if join_ is not None:
            return await self._all_unique(query)

        response = await self._all(query)
        return response
