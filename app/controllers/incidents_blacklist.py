from datetime import date

from app.controllers.incidents import get_branch_name, get_branch_timezone
from app.models import Incidents, Incidents_Blacklist
from app.repositories import Incidents_Blacklist_Repository
from app.schemas.responses import BlacklistIncidentResponse
from core.config import config
from core.controller import BaseController
from core.database import Propagation, Transactional
from core.exceptions import BadRequestException
from core.utils.datetime import convert_from_utc, get_duration_from_current_time

TIMEZONE = config.TIMEZONE


class Incidents_Blacklist_Controller(BaseController[Incidents_Blacklist]):
    def __init__(self, blacklist_repository: Incidents_Blacklist_Repository):
        super().__init__(model=Incidents_Blacklist, repository=blacklist_repository)
        self.blacklist_repository = blacklist_repository

    async def get_by_id(
        self, id: int, join_: set[str] | None = None
    ) -> Incidents_Blacklist | None:
        return await self.blacklist_repository.get_by_id(id=id, join_=join_)

    async def get_by_incident_id(
        self,
        incident_id: int,
    ) -> Incidents_Blacklist | None:
        return await self.blacklist_repository.get_by_incident_id(
            incident_id=incident_id
        )

    async def remove_from_blacklist(
        self,
        incident_id: int,
    ):
        blacklist = await self.blacklist_repository.get_by_incident_id(
            incident_id=incident_id
        )

        if blacklist is None:
            raise BadRequestException(message="No such incident exists")

        await self.blacklist_repository.session.delete(blacklist)
        await self.blacklist_repository.session.commit()

        return blacklist.incident_id

    async def get_blacklists(
        self,
        audit_controller,
        incidents_controller,
        customer_data_controller,
        customer_audit_controller,
        from_date: date | None,
        to_date: date | None,
        skip: int,
        limit: int,
        branch_id: int,
        is_test_user: bool = False,
    ):
        blacklisted_incidents = await self.blacklist_repository.get_blacklists(
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit,
            branch_id=branch_id,
            is_test_user=is_test_user,
            join_={"incidents"},
        )

        incidents_response = []

        profile_data = {}
        for blacklist, incident in blacklisted_incidents:
            prev_photo_url = None
            prev_incident_time = None
            prev_duration = None

            branch_timezone = await get_branch_timezone(incident.branch_id)

            if incident.incident_type == Incidents.IncidentType.PREVIOUSLY_BLACKLISTED:
                customer_obj = await customer_data_controller.get_by_id(
                    incident.customer_id
                )

                if customer_obj:
                    prev_photo_url = customer_obj.pic_url
                    prev_incident_time = customer_obj.visited_time
                    prev_duration = get_duration_from_current_time(
                        prev_incident_time, branch_timezone
                    )

                # watchlisted through incident
                if incident.previous_incident_id:
                    audits = await audit_controller.get_incident_audit(
                        incident_id=incident.previous_incident_id
                    )

                # watchlisted through faces
                elif incident.customer_id:
                    audits = await customer_audit_controller.get_customer_audit(
                        customer_id=incident.customer_id
                    )

                else:
                    audits = None

            else:
                audits = await audit_controller.get_incident_audit(
                    incident_id=incident.id
                )

            audit, profile = await incidents_controller.form_incidents_audit(
                branch_id=incident.branch_id,
                audits=audits,
                profile_data=profile_data,
            )

            profile_data = profile

            suspicious_incidents = await incidents_controller.get_suspicious_incidents(
                incident=incident
            )

            branch_name = await get_branch_name(branch_id=incident.branch_id)

            if branch_timezone is None:
                branch_timezone = TIMEZONE

            blacklisted_on = convert_from_utc(blacklist.created_at, branch_timezone)
            duration = get_duration_from_current_time(
                incident.incident_time, branch_timezone
            )

            response = BlacklistIncidentResponse(
                id=incident.id,
                uuid=incident.incident_id,
                incident_type=incident.incident_type,
                branch_id=incident.branch_id,
                branch_name=branch_name,
                blacklisted_on=blacklisted_on,
                prev_incident_id=blacklist.related_incident_id,
                incident_time=incident.incident_time,
                duration=duration,
                photo_url=incident.photo_url,
                video_url=incident.video_url,
                thumbnail_url=incident.thumbnail_url,
                suspicious_incidents=suspicious_incidents,
                name=incident.name,
                comments=incident.comments,
                match_score=incident.match_score,
                prev_photo_url=prev_photo_url,
                prev_incident_time=prev_incident_time,
                audit=audit,
                status=incident.status,
                is_blacklisted=incident.is_blacklisted,
                analyst_blacklisted=incident.analyst_blacklisted,
                is_valid=incident.is_valid,
                prev_duration=prev_duration,
            )
            incidents_response.append(response)

        return incidents_response

    async def get_blacklists_count(
        self,
        branch_id: int,
        from_date: date | None,
        to_date: date | None,
        is_test_user: bool = False,
    ):
        return await self.blacklist_repository.get_blacklists_count(
            from_date=from_date,
            to_date=to_date,
            branch_id=branch_id,
            is_test_user=is_test_user,
            join_={"incidents"},
        )

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(self, register_blacklist_request: dict) -> Incidents_Blacklist:
        blacklist = await self.blacklist_repository.get_by_incident_id(
            register_blacklist_request.get("incident_id")
        )

        if blacklist is None:
            return await self.blacklist_repository.create(register_blacklist_request)

        return blacklist
