from datetime import date, datetime

from sqlalchemy import Select
from sqlalchemy.sql.expression import or_, select

from app.models import Customers, Incidents, Incidents_Blacklist
from core.repository import BaseRepository


class Incidents_Blacklist_Repository(BaseRepository[Incidents_Blacklist]):
    """
    Incidents_Blacklist repository provides all the database operations for the Incidents_Blacklist model.
    """

    async def get_by_id(
        self, id: int, join_: set[str] | None
    ) -> Incidents_Blacklist | None:
        """
        Get Blacklist
        :param id: Blacklist id.
        :param join_: Join relations.
        :return: Incidents_Blacklist
        """
        if join_:
            query = select(self.model_class, Incidents, Customers)
        else:
            query = select(self.model_class)

        query = self._maybe_join(query, join_)
        query = query.filter(Incidents_Blacklist.id == id)

        result = await self.session.execute(query)
        return result.fetchone()

    async def get_by_incident_id(
        self, incident_id: int, join_: set[str] | None = None
    ) -> Incidents_Blacklist | None:
        """
        Get Blacklist
        :param incident_id: Incident id.
        :param join_: Join relations.
        :return: Incidents_Blacklist
        """

        query = await self._query(join_)
        query = query.filter(Incidents_Blacklist.incident_id == incident_id)

        if join_ is not None:
            return await self._all_unique(query)

        return await self._one_or_none(query)

    def _join_incidents(self, query: Select) -> Select:
        """
        Joins the Incidents_Blacklist table with the Incidents table.
        """
        return query.join(Incidents, Incidents.id == Incidents_Blacklist.incident_id)

    def _join_customers(self, query: Select) -> Select:
        """
        Joins the Incidents and Customers table with the Incidents_Blacklist table.
        """
        query = query.join(Incidents, Incidents.id == Incidents_Blacklist.incident_id)
        query = query.join(
            Customers,
            Incidents.customer_id == Customers.id,
            isouter=True,
        )
        return query

    async def get_blacklists(
        self,
        skip: int,
        limit: int,
        from_date: date | None,
        to_date: date | None,
        branch_id,
        is_test_user: bool,
        join_: set[str] | None = None,
    ) -> list[Incidents_Blacklist] | None:
        """
        Get Blacklisted incidents of a branch.
        :param branch_id: Branch id.
        :param join_: Join relations.
        :return: list[Incidents_Blacklist]
        """
        query = select(self.model_class, Incidents)
        query = self._maybe_join(query, join_)
        query = query.filter(Incidents.branch_id == branch_id)
        query = query.filter(Incidents.is_blacklisted.is_(True))

        if not is_test_user:
            query = query.filter(Incidents.is_test.is_(False))

        query = query.filter(
            or_(
                Incidents.analyst_blacklisted.is_(True),
                Incidents.status == Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
            )
        )

        if from_date:
            from_date = datetime.strptime(from_date.isoformat(), "%Y-%m-%d")
            query = query.filter(Incidents.incident_time >= from_date)

        if to_date:
            to_date = datetime.strptime(to_date.isoformat(), "%Y-%m-%d")
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.filter(Incidents.incident_time <= to_date)

        query = query.offset(skip).limit(limit)
        query = query.order_by(Incidents.incident_time.desc())

        result = await self.session.execute(query)
        return result.fetchall()

    async def get_blacklists_count(
        self,
        branch_id: int,
        from_date: date | None,
        to_date: date | None,
        is_test_user: bool,
        join_: set[str] | None = None,
    ):
        query = select(self.model_class, Incidents)
        query = self._maybe_join(query, join_)
        query = query.filter(Incidents.branch_id == branch_id)
        query = query.filter(Incidents.is_blacklisted.is_(True))

        if not is_test_user:
            query = query.filter(Incidents.is_test.is_(False))

        query = query.filter(
            or_(
                Incidents.analyst_blacklisted.is_(True),
                Incidents.status == Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
            )
        )

        if from_date:
            from_date = datetime.strptime(from_date.isoformat(), "%Y-%m-%d")
            query = query.filter(Incidents.incident_time >= from_date)

        if to_date:
            to_date = datetime.strptime(to_date.isoformat(), "%Y-%m-%d")
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.filter(Incidents.incident_time <= to_date)

        count = await self._count(query)
        return count
