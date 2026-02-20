from datetime import date, datetime

from sqlalchemy import Select, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql.expression import and_, or_, select
from sqlalchemy.types import Integer

from app.models import Incidents, Incidents_Blacklist
from core.config import config
from core.repository import BaseRepository


class IncidentsRepository(BaseRepository[Incidents]):
    """
    Incidents repository provides all the database operations for the Incidents model.
    """

    async def get_by_id(
        self, id: int, join_: set[str] | None = None
    ) -> Incidents | None:
        """
        Get Incident by id.
        :param int: Incident id.
        :param join_: Join relations.
        :return: Incidents.
        """
        query = await self._query(join_)
        query = query.filter(Incidents.id == id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)

    async def get_incident_by_incident_id(
        self, incident_id: str, join_: set[str] | None = None
    ) -> Incidents | None:
        """
        Get Incident by incident_id.
        :param incident_id: Incident incident_id.
        :param join_: Join relations.
        :return: Incidents.
        """
        query = await self._query(join_)
        query = query.filter(Incidents.incident_id == incident_id)
        if join_ is not None:
            return await self._all_unique(query)
        return await self._one_or_none(query)

    def _join_blacklists(self, query: Select) -> Select:
        """
        Joins the Incidents_Blacklist table with the Incidents table.
        """
        return query.join(
            Incidents_Blacklist,
            Incidents.id == Incidents_Blacklist.incident_id,
            isouter=True,
        )

    async def get_incidents_by_customer_id(
        self, incident: Incidents
    ) -> list[Incidents]:
        query = select(self.model_class)
        query = query.filter(
            Incidents.customer_id == incident.customer_id, Incidents.id != incident.id
        )

        query = query.limit(limit=5)

        return await self._all(query)

    async def get_incidents(
        self,
        skip: int,
        limit: int,
        sort: str | None,
        branch_ids: list[int],
        incident_filter: list[int],
        from_date: date,
        to_date: date,
        is_test_user: bool,
        join_: set[str] | None = None,
    ) -> list[Incidents] | None:
        """
        Get incidents of a branch.
        :param branch_ids: Branch id.
        :param join_: Join relations.
        :return: list[Incidents]
        """
        query = select(self.model_class, Incidents_Blacklist)
        query = self._maybe_join(query, join_)
        query = query.filter(Incidents.branch_id.in_(branch_ids))

        if not is_test_user:
            query = query.filter(Incidents.is_test.is_(False))

        filters = []
        if incident_filter:
            if config.BLACKLISTED in incident_filter:
                filters.append(
                    and_(
                        Incidents.status
                        != Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
                        Incidents.is_blacklisted.is_(True),
                        Incidents.analyst_blacklisted.is_(True),
                    )
                )

            if config.PREVIOUSLY_BLACKLISTED in incident_filter:
                filters.append(
                    and_(
                        Incidents.is_blacklisted.is_(True),
                        Incidents.status
                        == Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
                    )
                )

            if config.SENSITIVE in incident_filter:
                filters.append(
                    and_(
                        or_(
                            Incidents.is_blacklisted.is_not(True),
                            Incidents.analyst_blacklisted.is_not(True),
                        ),
                        Incidents.status
                        != Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
                        or_(
                            Incidents.is_valid
                            != Incidents.AnalystValidationChoices.VALID,
                            Incidents.is_valid.is_(None),
                        ),
                    )
                )

            if config.LIKELY_THEFT in incident_filter:
                filters.append(
                    and_(
                        or_(
                            Incidents.is_blacklisted.is_not(True),
                            Incidents.analyst_blacklisted.is_not(True),
                        ),
                        Incidents.status
                        != Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
                        Incidents.is_valid == Incidents.AnalystValidationChoices.VALID,
                    )
                )

        if filters:
            query = query.filter(or_(*filters))

        if from_date:
            from_date = datetime.strptime(from_date.isoformat(), "%Y-%m-%d")
            query = query.filter(Incidents.incident_time >= from_date)

        if to_date:
            to_date = datetime.strptime(to_date.isoformat(), "%Y-%m-%d")
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.filter(Incidents.incident_time <= to_date)

        query = query.offset(skip).limit(limit)

        if sort == "asc":
            query = query.order_by(Incidents.incident_time.asc())

        else:
            query = query.order_by(Incidents.incident_time.desc())

        result = await self.session.execute(query)

        return result.fetchall()

    async def get_branches_incidents_count(
        self,
        branch_ids: list[int],
        from_date: date,
        to_date: date,
        is_test_user: bool,
    ):
        if from_date:
            from_date = datetime.strptime(from_date.isoformat(), "%Y-%m-%d")

        if to_date:
            to_date = datetime.strptime(to_date.isoformat(), "%Y-%m-%d")
            to_date = to_date.replace(hour=23, minute=59, second=59)

        if is_test_user:
            statement = text(
                """
                    WITH branch_list AS (
                        SELECT unnest(:branch_ids) AS branch_id
                    )
                    SELECT
                        bl.branch_id AS id,

                        COUNT(CASE
                            WHEN (i.is_blacklisted IS NOT true OR i.analyst_blacklisted IS NOT true)
                                AND i.status != 4
                                AND i.is_valid = 1
                            THEN 1 END) AS likely_theft_count,

                        COUNT(CASE
                            WHEN (i.is_blacklisted IS NOT true OR i.analyst_blacklisted IS NOT true)
                                AND i.status != 4
                                AND (i.is_valid IS NULL OR i.is_valid != 1)
                            THEN 1 END) AS sensitive_theft_count,

                        COUNT(CASE
                            WHEN i.is_blacklisted IS true
                                AND (i.analyst_blacklisted IS true OR i.status = 4)
                            THEN 1 END) AS blacklist_count

                    FROM branch_list bl
                    LEFT JOIN incidents i
                        ON bl.branch_id = i.branch_id
                        AND i.incident_time >= :start_date
                        AND i.incident_time <= :end_date

                    GROUP BY bl.branch_id
                    ORDER BY likely_theft_count DESC;
                """
            )

        else:
            statement = text(
                """
                    WITH branch_list AS (
                        SELECT unnest(:branch_ids) AS branch_id
                    )
                    SELECT
                        bl.branch_id AS id,

                        COUNT(CASE
                            WHEN (i.is_blacklisted IS NOT true OR i.analyst_blacklisted IS NOT true)
                                AND i.status != 4
                                AND i.is_valid = 1
                                AND i.is_test is false
                            THEN 1 END) AS likely_theft_count,

                        COUNT(CASE
                            WHEN (i.is_blacklisted IS NOT true OR i.analyst_blacklisted IS NOT true)
                                AND i.status != 4
                                AND (i.is_valid IS NULL OR i.is_valid != 1)
                                AND i.is_test is false
                            THEN 1 END) AS sensitive_theft_count,

                        COUNT(CASE
                            WHEN i.is_blacklisted IS true
                                AND (i.analyst_blacklisted IS true OR i.status = 4)
                                AND i.is_test is false
                            THEN 1 END) AS blacklist_count

                    FROM branch_list bl
                    LEFT JOIN incidents i
                        ON bl.branch_id = i.branch_id
                        AND i.incident_time >= :start_date
                        AND i.incident_time <= :end_date

                    GROUP BY bl.branch_id
                    ORDER BY likely_theft_count DESC;
                """
            )

        statement = statement.bindparams(
            bindparam("branch_ids", type_=ARRAY(Integer)),
            bindparam("start_date"),
            bindparam("end_date"),
        )

        result = await self.session.execute(
            statement,
            {"branch_ids": branch_ids, "start_date": from_date, "end_date": to_date},
        )
        return result.mappings().all()

    async def get_incidents_count(
        self,
        branch_ids: list[int],
        incident_filter: list[int],
        from_date: date,
        to_date: date,
        is_test_user: bool,
        join_: set[str] | None = None,
    ) -> int:
        query = await self._query(join_)
        query = query.filter(Incidents.branch_id.in_(branch_ids))

        if not is_test_user:
            query = query.filter(Incidents.is_test.is_(False))

        filters = []
        if incident_filter:
            if config.BLACKLISTED in incident_filter:
                filters.append(
                    and_(
                        Incidents.status
                        != Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
                        Incidents.is_blacklisted.is_(True),
                        Incidents.analyst_blacklisted.is_(True),
                    )
                )

            if config.PREVIOUSLY_BLACKLISTED in incident_filter:
                filters.append(
                    and_(
                        Incidents.is_blacklisted.is_(True),
                        Incidents.status
                        == Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
                    )
                )

            if config.SENSITIVE in incident_filter:
                filters.append(
                    and_(
                        or_(
                            Incidents.is_blacklisted.is_not(True),
                            Incidents.analyst_blacklisted.is_not(True),
                        ),
                        Incidents.status
                        != Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
                        or_(
                            Incidents.is_valid
                            != Incidents.AnalystValidationChoices.VALID,
                            Incidents.is_valid.is_(None),
                        ),
                    )
                )

            if config.LIKELY_THEFT in incident_filter:
                filters.append(
                    and_(
                        or_(
                            Incidents.is_blacklisted.is_not(True),
                            Incidents.analyst_blacklisted.is_not(True),
                        ),
                        Incidents.status
                        != Incidents.IncidentStatus.PREVIOUSLY_BLACKLISTED,
                        Incidents.is_valid == Incidents.AnalystValidationChoices.VALID,
                    )
                )

        if filters:
            query = query.filter(or_(*filters))

        if from_date:
            from_date = datetime.strptime(from_date.isoformat(), "%Y-%m-%d")
            query = query.filter(Incidents.incident_time >= from_date)

        if to_date:
            to_date = datetime.strptime(to_date.isoformat(), "%Y-%m-%d")
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.filter(Incidents.incident_time <= to_date)

        return await self._count(query)

    async def get_blacklisted_incidents(
        self,
        branch_id: int,
        join_ = None,
    ):
        query = await self._query(join_)
        query = query.filter(
            Incidents.branch_id == branch_id,
            Incidents.incident_type == Incidents.IncidentType.CUSTOMER_THEFT,
            Incidents.is_blacklisted.is_(True),
            Incidents.analyst_blacklisted.is_(True)
        )
        return await self._all(query)
