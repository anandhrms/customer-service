from datetime import datetime
from app.models import BlacklistSentLogs
from core.repository import BaseRepository


class BlacklistSentLogsRepository(BaseRepository[BlacklistSentLogs]):
    """
    BlacklistSentLogsRepository provides all the database operations for the BlacklistSentLogs model.
    """

    async def get_by_id(
        self, id: int, join_: set[str] | None = None
    ) -> BlacklistSentLogs | None:
        """
        Get BlacklistSentLogs by id.
        :param int: BlacklistSentLogs id.
        :param join_: Join relations.
        :return: BlacklistSentLogs.
        """
        query = await self._query(join_)
        query = query.filter(BlacklistSentLogs.id == id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)
    
    async def get_blacklist_log(self, branch_id: int, created_at: datetime, join_ = None,):
        query = await self._query(join_)
        query = query.filter(
            BlacklistSentLogs.branch_id == branch_id,
            BlacklistSentLogs.created_at >= created_at
            # Incidents.incident_type == Incidents.IncidentType.CUSTOMER_THEFT,
            # Incidents.is_blacklisted.is_(True),
            # Incidents.analyst_blacklisted.is_(True)
        )
        return await self._all(query)
        
