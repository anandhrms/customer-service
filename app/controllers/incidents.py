from datetime import date, datetime

import pytz

from app.library import entity
from app.models import Incidents
from app.repositories import IncidentsRepository
from app.schemas.requests import (
    BlacklistIncidentRequest,
    UpdateIncidentRequest,
    ValidateIncidentRequest,
)
from app.schemas.responses import (
    AuditResponse,
    BranchIncidentsCountResponse,
    IncidentResponse,
    SuspiciousIncidentsResponse,
    UserResponse,
)
from core.cache import Cache
from core.config import config
from core.controller import BaseController
from core.database import Propagation, Transactional
from core.exceptions import BadRequestException
from core.library.logging import logger
from core.utils.datetime import convert_from_utc, get_duration_from_current_time

TIMEZONE = config.TIMEZONE


async def get_branch_timezone(branch_id: int):
    branch_timezone = await Cache.get_branch_timezone(branch_id)

    if branch_timezone:
        return branch_timezone

    return await entity.get_branch_timezone(branch_id)


async def get_branch_name(branch_id: int):
    branch_name = await Cache.get_branch_name(branch_id)

    if branch_name:
        return branch_name

    return await entity.get_branch_name(branch_id)


class IncidentsController(BaseController[Incidents]):
    def __init__(self, incidents_repository: IncidentsRepository):
        super().__init__(model=Incidents, repository=incidents_repository)
        self.incidents_repository = incidents_repository

    async def get_incident_by_incident_id(self, incident_id: str) -> Incidents | None:
        return await self.incidents_repository.get_incident_by_incident_id(
            incident_id=incident_id
        )

    async def get_incident_by_id(self, incident_id) -> Incidents:
        incident = await self.incidents_repository.get_by_id(id=incident_id)

        if incident is None:
            raise BadRequestException(message="No such incident exists")

        return incident

    async def get_incidents_by_customer_id(
        self, incident: Incidents
    ) -> list[Incidents]:
        return await self.incidents_repository.get_incidents_by_customer_id(
            incident=incident
        )

    async def update_incident_share_video_url(self, incident_id: int, video_url: str):
        incident = await self.get_incident_by_id(incident_id)
        incident.share_video_url = video_url
        await self.incidents_repository.session.commit()
        return incident

    async def get_suspicious_incidents(
        self, incident: Incidents
    ) -> list[SuspiciousIncidentsResponse]:
        customer_id = incident.customer_id

        if customer_id is None:
            return []

        suspicious_incidents = await self.get_incidents_by_customer_id(incident)

        suspicious_incidents_response = []
        for suspicious_incident in suspicious_incidents:
            suspicious_incidents_response.append(
                SuspiciousIncidentsResponse(
                    incident_id=suspicious_incident.id,
                    video_url=suspicious_incident.video_url,
                    photo_url=suspicious_incident.photo_url,
                    thumbnail_url=suspicious_incident.thumbnail_url,
                    is_valid=suspicious_incident.is_valid,
                    incident_time=suspicious_incident.incident_time,
                    comments=suspicious_incident.comments,
                )
            )

        return suspicious_incidents_response

    async def get_incidents_count(
        self,
        incident_filter: list[int],
        branch_ids: list[int],
        from_date: date,
        to_date: date,
        is_test_user: bool = False,
    ):
        count = await self.incidents_repository.get_incidents_count(
            branch_ids=branch_ids,
            incident_filter=incident_filter,
            from_date=from_date,
            to_date=to_date,
            is_test_user=is_test_user,
        )

        sensitive_theft_count = await self.incidents_repository.get_incidents_count(
            branch_ids=branch_ids,
            incident_filter=[config.SENSITIVE],
            from_date=from_date,
            to_date=to_date,
            is_test_user=is_test_user,
        )

        likely_theft_count = await self.incidents_repository.get_incidents_count(
            branch_ids=branch_ids,
            incident_filter=[config.LIKELY_THEFT],
            from_date=from_date,
            to_date=to_date,
            is_test_user=is_test_user,
        )

        blacklisted_count = await self.incidents_repository.get_incidents_count(
            branch_ids=branch_ids,
            incident_filter=[config.BLACKLISTED],
            from_date=from_date,
            to_date=to_date,
            is_test_user=is_test_user,
        )

        previously_blacklisted_count = (
            await self.incidents_repository.get_incidents_count(
                branch_ids=branch_ids,
                incident_filter=[config.PREVIOUSLY_BLACKLISTED],
                from_date=from_date,
                to_date=to_date,
                is_test_user=is_test_user,
            )
        )

        response = {
            "count": count,
            "sensitive_theft_count": sensitive_theft_count,
            "likely_theft_count": likely_theft_count,
            "blacklisted_count": blacklisted_count,
            "previously_blacklisted_count": previously_blacklisted_count,
        }

        return response

    async def get_branches_incidents_count(
        self,
        branch_ids: list[int],
        from_date: date,
        to_date: date,
        is_test_user: bool = False,
    ):
        branch_incidents_count = (
            await self.incidents_repository.get_branches_incidents_count(
                from_date=from_date,
                to_date=to_date,
                branch_ids=branch_ids,
                is_test_user=is_test_user,
            )
        )

        response = []
        for branch in branch_incidents_count:
            response.append(
                BranchIncidentsCountResponse(
                    **branch,
                    branch_name=await get_branch_name(branch["id"]),
                )
            )

        return response

    async def form_incidents_audit(
        self,
        branch_id: int,
        audits: list | None,
        profile_data: dict | None = None,
    ) -> list[AuditResponse]:
        if not audits:
            audit = None

        else:
            audit = []
            for i in audits:
                user_id = i.updated_by

                if user_id in profile_data:
                    profile_response = profile_data.get(user_id)

                else:
                    profile_response = await entity.get_profile(user_id=user_id)
                    profile_data[user_id] = profile_response

                branch_timezone = await get_branch_timezone(branch_id)
                if branch_timezone is None:
                    branch_timezone = TIMEZONE

                updated_at = convert_from_utc(i.updated_at, branch_timezone)

                audit.append(
                    AuditResponse(
                        audit_id=i.id,
                        action_type=i.action_type,
                        updated_at=updated_at,
                        updated_by=UserResponse(user_id=user_id, **profile_response),
                        comments=i.comments,
                        status=i.status,
                        edited=i.edited,
                    )
                )

        return audit, profile_data

    async def get_incidents(
        self,
        audit_controller,
        customer_audit_controller,
        customer_data_controller,
        incident_filter: list[int],
        from_date: date,
        to_date: date,
        skip: int,
        limit: int,
        sort: str | None,
        branch_ids: list[int],
        is_test_user: bool = False,
    ) -> list[IncidentResponse]:
        incidents = await self.incidents_repository.get_incidents(
            skip=skip,
            limit=limit,
            sort=sort,
            branch_ids=branch_ids,
            incident_filter=incident_filter,
            from_date=from_date,
            to_date=to_date,
            is_test_user=is_test_user,
            join_={"blacklists"},
        )

        incidents_response = []

        profile_data = {}
        for incident, blacklist in incidents:
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

            audit, profile = await self.form_incidents_audit(
                branch_id=incident.branch_id,
                audits=audits,
                profile_data=profile_data,
            )

            profile_data = profile

            suspicious_incidents = await self.get_suspicious_incidents(
                incident=incident
            )

            branch_name = await get_branch_name(branch_id=incident.branch_id)

            if branch_timezone is None:
                branch_timezone = TIMEZONE

            duration = get_duration_from_current_time(
                incident.incident_time, branch_timezone
            )

            if blacklist:
                blacklisted_on = convert_from_utc(blacklist.created_at, branch_timezone)
                prev_incident_id = blacklist.related_incident_id

            else:
                blacklisted_on = None
                prev_incident_id = None

            response = IncidentResponse(
                id=incident.id,
                uuid=incident.incident_id,
                branch_id=incident.branch_id,
                branch_name=branch_name,
                incident_time=incident.incident_time,
                duration=duration,
                incident_type=incident.incident_type,
                photo_url=incident.photo_url,
                video_url=incident.video_url,
                thumbnail_url=incident.thumbnail_url,
                suspicious_incidents=suspicious_incidents,
                name=incident.name,
                status=incident.status,
                comments=incident.comments,
                is_blacklisted=incident.is_blacklisted,
                match_score=incident.match_score,
                prev_photo_url=prev_photo_url,
                prev_incident_time=prev_incident_time,
                analyst_blacklisted=incident.analyst_blacklisted,
                is_valid=incident.is_valid,
                blacklisted_on=blacklisted_on,
                prev_incident_id=prev_incident_id,
                prev_duration=prev_duration,
                audit=audit,
                response=incident.response,
            )
            incidents_response.append(response)

        return incidents_response

    async def update_incident(
        self,
        user_id: int,
        update_incident_request: UpdateIncidentRequest,
    ):
        incident = await self.get_by_id(id_=update_incident_request.id)

        incident.status = update_incident_request.status
        incident.updated_by = user_id
        incident.updated_at = datetime.now(pytz.utc)

        await self.incidents_repository.session.commit()

        return incident

    async def remove_from_blacklists(
        self,
        incident_id: int,
        user_id: int,
    ) -> Incidents | int | None:
        incident = await self.get_incident_by_id(incident_id)

        # for watchlist re-entry, previous incident/face needs to be removed from watchlist
        if incident.incident_type == Incidents.IncidentType.PREVIOUSLY_BLACKLISTED:
            incident.is_blacklisted = False

            if incident.previous_incident_id:
                previous_incident = await self.get_incident_by_id(
                    incident.previous_incident_id
                )
                if previous_incident.is_blacklisted:
                    previous_incident.is_blacklisted = False
                    previous_incident.updated_by = user_id
                    await self.incidents_repository.session.commit()
                    return previous_incident
                raise BadRequestException(
                    "Incident is not watchlisted or removed from watchlist"
                )

            elif incident.customer_id:
                return incident.customer_id

            else:
                return None

        else:
            incident.is_blacklisted = False
            incident.updated_by = user_id

            await self.incidents_repository.session.commit()

            return incident

    async def get_incident_details(
        self,
        incident_id: int,
        audit_controller,
        blacklist_controller,
        customer_data_controller,
        customer_audit_controller,
    ):
        incident = await self.get_incident_by_id(incident_id)
        branch_timezone = await get_branch_timezone(incident.branch_id)

        prev_photo_url = None
        prev_incident_time = None
        prev_duration = None

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
            audits = await audit_controller.get_incident_audit(incident_id=incident.id)

        blacklist = await blacklist_controller.blacklist_repository.get_by_incident_id(
            incident_id=incident_id
        )

        if branch_timezone is None:
            branch_timezone = TIMEZONE

        if blacklist:
            blacklisted_on = convert_from_utc(blacklist.created_at, branch_timezone)
            prev_incident_id = blacklist.related_incident_id

        else:
            blacklisted_on = None
            prev_incident_id = None

        profile_data = {}

        audit, _ = await self.form_incidents_audit(
            branch_id=incident.branch_id,
            audits=audits,
            profile_data=profile_data,
        )

        suspicious_incidents = await self.get_suspicious_incidents(incident=incident)
        branch_name = await get_branch_name(branch_id=incident.branch_id)
        duration = get_duration_from_current_time(
            incident.incident_time, branch_timezone
        )

        response = IncidentResponse(
            id=incident.id,
            uuid=incident.incident_id,
            branch_id=incident.branch_id,
            branch_name=branch_name,
            incident_time=incident.incident_time,
            duration=duration,
            incident_type=incident.incident_type,
            photo_url=incident.photo_url,
            video_url=incident.video_url,
            thumbnail_url=incident.thumbnail_url,
            suspicious_incidents=suspicious_incidents,
            name=incident.name,
            status=incident.status,
            comments=incident.comments,
            match_score=incident.match_score,
            prev_photo_url=prev_photo_url,
            prev_incident_time=prev_incident_time,
            is_blacklisted=incident.is_blacklisted,
            analyst_blacklisted=incident.analyst_blacklisted,
            is_valid=incident.is_valid,
            blacklisted_on=blacklisted_on,
            prev_incident_id=prev_incident_id,
            prev_duration=prev_duration,
            audit=audit,
            response=incident.response,
        )

        return response

    async def map_customer(
        self,
        incident_obj: Incidents,
        validate_incident_request: ValidateIncidentRequest,
        customer_id: int | None = None,
    ):
        incident_obj.customer_id = customer_id
        incident_obj.validated_by = validate_incident_request.validated_by
        incident_obj.analyst_comments = validate_incident_request.comments

        await self.incidents_repository.session.commit()

        return incident_obj

    async def validate_incident(
        self,
        incident_obj: Incidents,
        validate_incident_request: ValidateIncidentRequest,
    ):
        incident_obj.is_valid = validate_incident_request.is_valid

        incident_obj.validated_by = validate_incident_request.validated_by
        incident_obj.analyst_comments = validate_incident_request.comments

        await self.incidents_repository.session.commit()

        return incident_obj

    async def validate_incident_test(
        self,
        incident_obj: Incidents,
        validate_incident_request: ValidateIncidentRequest,
    ):
        incident_obj.is_valid = validate_incident_request.is_valid

        await self.incidents_repository.session.commit()

        return incident_obj

    async def update_blacklist_status(
        self, user_id: int, update_incident_request: BlacklistIncidentRequest
    ):
        incident = await self.get_incident_by_id(update_incident_request.id)

        if incident.is_blacklisted:
            raise BadRequestException("Incident is already blacklisted")

        update_status = False
        if incident.status != update_incident_request.status:
            update_status = True

        incident.is_blacklisted = True
        incident.status = update_incident_request.status
        incident.updated_by = user_id
        incident.updated_at = datetime.now(pytz.utc)
        await self.incidents_repository.session.commit()

        return incident, update_status

    async def analyst_blacklist(
        self,
        incident_id: str,
        blacklist_status: bool,
    ):
        incident = await self.get_incident_by_incident_id(incident_id)

        if incident is None:
            raise BadRequestException("No incident exists with this id")

        if incident.analyst_blacklisted == blacklist_status:
            raise BadRequestException("Incident is already in this state")

        incident.analyst_blacklisted = blacklist_status
        await self.incidents_repository.session.commit()

        return incident
    async def get_blacklisted_incidents(
        self,
        branch_id: int,
    ) -> list[Incidents]:
        return await self.incidents_repository.get_blacklisted_incidents(branch_id)

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(
        self, register_incident_request: dict, user_id: int | None = None
    ) -> Incidents:
        related_incident_id = register_incident_request.get("prev_inci_id")

        if register_incident_request.get("created_at"):
            try:
                incident_logged_time = register_incident_request["created_at"].replace(
                    " at ", " "
                )
                incident_logged_time = datetime.strptime(
                    incident_logged_time, "%B %d, %Y %I:%M:%S %p UTC%z"
                )

            except Exception:
                try:
                    incident_logged_time = datetime.strptime(
                        incident_logged_time, "%Y-%m-%d %H:%M:%S"
                    )

                except Exception as e:
                    logger.error(f"Error in incident logging time: {str(e)}")
                    incident_logged_time = None

        else:
            incident_logged_time = None

        try:
            incident_time = datetime.strptime(
                register_incident_request["inci_time"], "%Y-%m-%d %H:%M:%S"
            )

        except Exception:
            incident_time = datetime.strptime(
                register_incident_request["inci_time"], "%B %d, %Y %H:%M:%S"
            )

        analyst_blacklisted = None
        if related_incident_id:
            related_incident = await self.get_incident_by_incident_id(
                incident_id=related_incident_id
            )
            if related_incident is None:
                logger.error(
                    "No incident exists with this previous incident incident_id"
                )
                return

            related_incident_id = related_incident.id

        if (
            register_incident_request["inci_type"]
            == Incidents.IncidentType.PREVIOUSLY_BLACKLISTED
        ):
            analyst_blacklisted = True

        incidents_data = {
            "incident_id": register_incident_request["inci_id"],
            "camera_id": register_incident_request["camera_id"],
            "company_id": register_incident_request["company_id"],
            "branch_id": register_incident_request["branch_id"],
            "thumbnail_url": register_incident_request.get("thumb_image"),
            "name": register_incident_request["name"],
            "incident_type": register_incident_request["inci_type"],
            "no_of_visits": register_incident_request.get("no_of_visits", 1),
            "incident_time": incident_time,
            "incident_logged_time": incident_logged_time,
            "comments": register_incident_request["comments"],
            "photo_url": register_incident_request["pic_url"],
            "video_url": register_incident_request["video_url"],
            "previous_incident_id": related_incident_id,
            "probable_customer_ids": register_incident_request.get("probable_cust_ids"),
            "customer_id": register_incident_request.get("customer_id"),
            "status": register_incident_request["status"],
            "is_blacklisted": register_incident_request["is_blacklisted"],
            "response": register_incident_request.get("response"),
            "analyst_blacklisted": analyst_blacklisted,
            "is_valid": register_incident_request.get("is_valid"),
            "analyst_incident_type": register_incident_request["inci_type"],
            "is_test": register_incident_request.get("is_test", False),
            "match_score": register_incident_request.get("match_score"),
            "updated_by": user_id,
            "created_at": datetime.now(pytz.utc),
            "updated_at": datetime.now(pytz.utc),
        }

        return await self.incidents_repository.create(incidents_data)
