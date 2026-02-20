from app.models import Incidents_Audit
from core.repository import BaseRepository


class IncidentsAuditRepository(BaseRepository[Incidents_Audit]):
    """
    IncidentsAudit repository provides all the database operations for the IncidentsAudit model.
    """

    async def get_by_id(
        self, id: int, join_: set[str] | None = None
    ) -> Incidents_Audit | None:
        """
        Get Incidents_Audit by id.
        :param int: Incidents_Audit id.
        :param join_: Join relations.
        :return: Incidents_Audit.
        """
        query = await self._query(join_)
        query = query.filter(Incidents_Audit.id == id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)

    async def get_incident_audit(self, incident_id: int, join_: set[str] | None = None):
        query = await self._query(join_)
        query = query.filter(
            Incidents_Audit.incident_id == incident_id,
        )
        query = query.order_by(Incidents_Audit.created_at.desc())

        if join_ is not None:
            return await self._all_unique(query)

        return await self._all(query)
