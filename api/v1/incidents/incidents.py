import asyncio
from datetime import date, datetime
from typing import Annotated
import requests

import pytz
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
)

from app.controllers import (
    CloudDBController,
    CustomerDataController,
    CustomersAuditController,
    ErrorLogsController,
    EvidenceDataController,
    Incidents_Blacklist_Controller,
    IncidentsAnalystAuditController,
    IncidentsAuditController,
    IncidentsController,
)
from app.library.entity_service import entity
from app.library.helpers import add_incident, send_notification
from app.library.websocket_service.blacklist import BlacklistWebsocketService
from app.models import Incidents, Incidents_Analyst_Audit, Incidents_Audit
from app.schemas.requests import (
    AnalystBlacklistIncidentRequest,
    CreateIncidentRequest,
    CreateIncidentTestRequest,
    EditIncidentCommentsRequest,
    UpdateIncidentRequest,
    ValidateIncidentRequest,
    ValidateIncidentTestRequest,
)
from app.schemas.responses import CreateIncidentResponse, UpdateIncidentResponse
from app.utils.add_logo import VideoLogoOverlay
from core.config import config
from core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from core.factory import Factory
from core.fastapi.dependencies import AuthenticationRequired
from core.library import logger

incident_router = APIRouter()

controller_factory = Factory()

ESCAPE_THEFT_TEMPLATE = config.ESCAPE_THEFT_TEMPLATE
THEFT_STOPPED_TEMPLATE = config.THEFT_STOPPED_TEMPLATE

ESCAPE_THEFT_GROUP = config.ESCAPE_THEFT
THEFT_STOPPED_GROUP = config.THEFT_STOPPED

NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON = (
    config.NOTIFICATION_GROUP_TYPE_BLACKLISTED_PERSON
)
NOTIFICATION_GROUP_TYPE_THEFT_STOPPED = config.NOTIFICATION_GROUP_TYPE_THEFT_STOPPED
NOTIFICATION_GROUP_TYPE_ESCAPE_THEFT = config.NOTIFICATION_GROUP_TYPE_ESCAPE_THEFT
NOTIFICATION_GROUP_TYPE_CAMERA_DOWN = config.NOTIFICATION_GROUP_TYPE_CAMERA_DOWN
NOTIFICATION_TYPE_PUSH_NOTIFICATION = config.NOTIFICATION_TYPE_PUSH_NOTIFICATION
NOTIFICATION_TYPE_BLACKLIST_ALERT = config.NOTIFICATION_TYPE_BLACKLIST_ALERT


@incident_router.get(
    "/",
    status_code=200,
    tags=["Incidents"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_incidents(
    request: Request,
    branch_ids: Annotated[list[int], Query(description="Mention the branch ids")],
    incident_filter: Annotated[
        list[int] | None,
        Query(
            description=f"""
            Sensitive : {config.SENSITIVE},
            Likely Theft: {config.LIKELY_THEFT},
            Blacklisted: {config.BLACKLISTED},
            Previously Blacklisted: {config.PREVIOUSLY_BLACKLISTED}
        """,
            example=[0, 1],
        ),
    ] = None,
    from_date: Annotated[
        date | None,
        Query(
            description="Mention the start date in YYYY-MM-DD format",
            example="2024-09-27",
        ),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(
            description="Mention the end date in YYYY-MM-DD format",
            example="2024-09-30",
        ),
    ] = None,
    offset: Annotated[
        int | None,
        Query(
            description="Mention number of data to be skipped",
            ge=0,
            le=9223372036854775807,
        ),
    ] = None,
    limit: Annotated[
        int | None,
        Query(
            description="Mention number of data to be received",
            ge=0,
            le=9223372036854775807,
        ),
    ] = None,
    sort: Annotated[
        str | None,
        Query(
            description="Mention the field to be sorted",
        ),
    ] = None,
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    audit_controller: IncidentsAuditController = Depends(
        controller_factory.get_audit_controller
    ),
    customer_audit_controller: CustomersAuditController = Depends(
        controller_factory.get_customer_audit_controller
    ),
    customer_data_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
):
    try:
        is_test_user = (
            False if request.user.role_id != config.SUPER_USER_ROLE_ID else True
        )

        return await incidents_controller.get_incidents(
            audit_controller=audit_controller,
            customer_audit_controller=customer_audit_controller,
            customer_data_controller=customer_data_controller,
            incident_filter=incident_filter,
            from_date=from_date,
            to_date=to_date,
            skip=offset,
            limit=limit,
            sort=sort,
            branch_ids=branch_ids,
            is_test_user=is_test_user,
        )

    except Exception as e:
        logger.error(f"GET /incidents/ : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.get(
    "/branches",
    status_code=200,
    tags=["Incidents"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_branches_incidents(
    request: Request,
    branch_ids: Annotated[list[int], Query(description="Mention the branch ids")],
    from_date: Annotated[
        date | None,
        Query(
            description="Mention the start date in YYYY-MM-DD format",
            example="2024-09-27",
        ),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(
            description="Mention the end date in YYYY-MM-DD format",
            example="2024-09-30",
        ),
    ] = None,
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
):
    try:
        is_test_user = (
            False if request.user.role_id != config.SUPER_USER_ROLE_ID else True
        )

        branch_hardware_status_task = entity.get_hardware_status(branch_ids)
        branch_camera_status_task = entity.get_camera_status(branch_ids)

        branch_data_task = incidents_controller.get_branches_incidents_count(
            from_date=from_date,
            to_date=to_date,
            branch_ids=branch_ids,
            is_test_user=is_test_user,
        )

        (
            branch_hardware_status,
            branch_camera_status,
            branch_data,
        ) = await asyncio.gather(
            branch_hardware_status_task,
            branch_camera_status_task,
            branch_data_task,
            return_exceptions=True,
        )

        response = []
        for record in branch_data:
            # Hardware status
            hardware_status = branch_hardware_status.get(str(record.id), 1)
            record.hardware_status = hardware_status
            if hardware_status == 0:
                record.hardware_down_content = config.HARDWARE_OFFLINE_CONTENT
                record.hardware_troubleshoot = config.HARDWARE_TROUBLESHOOT_ENABLED
                record.hardware_troubleshoot_url = config.HARDWARE_TROUBLESHOOT_URL

            # Camera status
            camera_status = branch_camera_status.get(str(record.id), 1)
            offline_camera_ids = branch_camera_status.get("offline_camera_ids")
            record.camera_status = camera_status
            if camera_status == 0:
                if len(offline_camera_ids) > 1:
                    dynamic_content = f"IDs ({','.join(offline_camera_ids)}) are"
                else:
                    dynamic_content = f"ID ({offline_camera_ids[0]}) is"

                record.camera_down_content = config.CAMERA_OFFLINE_CONTENT.replace(
                    "{{ids}}", dynamic_content
                )

            response.append(record)

        return response

    except Exception as e:
        logger.error(f"GET /incidents/branches : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.get(
    "/count",
    status_code=200,
    tags=["Incidents"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_incidents_count(
    request: Request,
    branch_ids: Annotated[list[int], Query(description="Mention the branch ids")],
    incident_filter: Annotated[
        list[int] | None,
        Query(
            description=f"""
            Sensitive : {config.SENSITIVE},
            Likely Theft: {config.LIKELY_THEFT},
            Blacklisted: {config.BLACKLISTED},
            Previously Blacklisted: {config.PREVIOUSLY_BLACKLISTED}
        """,
            example=[0, 1],
        ),
    ] = None,
    from_date: Annotated[
        date | None,
        Query(
            description="Mention the start date in YYYY-MM-DD format",
            example="2024-09-27",
        ),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(
            description="Mention the end date in YYYY-MM-DD format",
            example="2024-09-30",
        ),
    ] = None,
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
):
    try:
        is_test_user = (
            False if request.user.role_id != config.SUPER_USER_ROLE_ID else True
        )

        return await incidents_controller.get_incidents_count(
            incident_filter=incident_filter,
            from_date=from_date,
            to_date=to_date,
            branch_ids=branch_ids,
            is_test_user=is_test_user,
        )

    except Exception as e:
        logger.error(f"GET /incidents/count : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.post(
    "/",
    tags=["Incidents"],
    # dependencies=[Depends(AuthenticationRequired)],
)
async def add_incident_from_ds(
    incident_request: CreateIncidentRequest,
):
    try:
        logger.info(f"Received incident: {incident_request.model_dump()}")
        await add_incident(incident_request.model_dump())
        return {"status": "success"}

    except ForbiddenException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        error_logs = {
            "inci_id": incident_request.inci_id,
            "error": str(e),
        }
        logger.error(f"POST /incidents/ : {error_logs}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.post(
    "/test",
    tags=["Incidents"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def create_incident_test(
    request: Request,
    incident_request: CreateIncidentTestRequest,
    firestore_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
):
    try:
        incident_data = firestore_controller.publish_incident(
            incident_request.model_dump()
        )

        return CreateIncidentResponse(inci_id=incident_data["inci_id"]).model_dump()

    except ForbiddenException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"POST /incidents/test : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.put(
    "/",
    status_code=200,
    tags=["Incidents"],
    dependencies=[Depends(AuthenticationRequired)],
    response_model=UpdateIncidentResponse,
)
async def update_incident_status(
    background_tasks: BackgroundTasks,
    request: Request,
    update_incident_request: UpdateIncidentRequest,
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    audit_controller: IncidentsAuditController = Depends(
        controller_factory.get_audit_controller
    ),
):
    try:
        incident = await incidents_controller.update_incident(
            user_id=request.user.id,
            update_incident_request=update_incident_request,
        )

        if update_incident_request.status == Incidents.IncidentStatus.ESCAPE_THEFT:
            background_tasks.add_task(
                send_notification,
                incident.branch_id,
                ESCAPE_THEFT_TEMPLATE,
                incident.id,
                ESCAPE_THEFT_GROUP,
                NOTIFICATION_GROUP_TYPE_ESCAPE_THEFT,
                None,
                request.user.id,
            )

        if update_incident_request.status == Incidents.IncidentStatus.THEFT_STOPPED:
            background_tasks.add_task(
                send_notification,
                incident.branch_id,
                THEFT_STOPPED_TEMPLATE,
                incident.id,
                THEFT_STOPPED_GROUP,
                NOTIFICATION_GROUP_TYPE_THEFT_STOPPED,
                None,
                request.user.id,
            )

        await audit_controller.register(
            {
                "incident_id": incident.id,
                "action_type": update_incident_request.status,
                "status": Incidents_Audit.AuditStatus.ADDED,
                "comments": update_incident_request.comments,
                "created_by": request.user.id,
                "updated_by": request.user.id,
                "created_at": datetime.now(pytz.utc),
                "updated_at": datetime.now(pytz.utc),
            }
        )

        return UpdateIncidentResponse().model_dump()

    except Exception as e:
        logger.error(f"PUT /incidents/ : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.patch(
    "/validate",
    status_code=200,
    tags=["Incidents"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def validate_incident_test(
    validate_incident_request: ValidateIncidentTestRequest,
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
):
    try:
        incident_obj = await incidents_controller.get_incident_by_id(
            incident_id=validate_incident_request.incident_id
        )

        if incident_obj is None:
            raise NotFoundException("No such incident exists with this id")

        await incidents_controller.validate_incident_test(
            incident_obj=incident_obj,
            validate_incident_request=validate_incident_request,
        )

        if (
            validate_incident_request.is_valid
            == Incidents.AnalystValidationChoices.VALID
        ):
            await send_notification(
                branch_id=incident_obj.branch_id,
                template=config.LIKELY_THEFT_ALERT_TEMPLATE,
                incident=incident_obj,
                group=config.LIKELY_THEFT,
                notification_group_type=config.NOTIFICATION_GROUP_TYPE_LIKELY_THEFT,
                channel_id=config.NOTIFICATION_CHANNEL_LIKELY_THEFT_ALERT,
                sound_name=config.NOTIFICATION_SOUND_LIKELY_THEFT_ALERT,
            )

        return {"status": "success"}

    except NotFoundException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"PATCH /incidents/validate : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.patch(
    "/",
    status_code=200,
    tags=["Incidents"],
)
async def validate_incident(
    validate_incident_request: ValidateIncidentRequest,
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    customer_data_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    error_logs_controller: ErrorLogsController = Depends(
        controller_factory.get_error_logs_controller
    ),
):
    try:
        incident_obj = await incidents_controller.get_incident_by_incident_id(
            incident_id=validate_incident_request.incident_id
        )

        if incident_obj is None:
            raise NotFoundException(
                f"No such incident exists with this id: {validate_incident_request.incident_id}"
            )

        if validate_incident_request.is_valid is not None:
            await incidents_controller.validate_incident(
                incident_obj=incident_obj,
                validate_incident_request=validate_incident_request,
            )

            if (
                validate_incident_request.is_valid
                == Incidents.AnalystValidationChoices.VALID
            ):
                await send_notification(
                    branch_id=incident_obj.branch_id,
                    template=config.LIKELY_THEFT_ALERT_TEMPLATE,
                    incident=incident_obj,
                    group=config.LIKELY_THEFT,
                    notification_group_type=config.NOTIFICATION_GROUP_TYPE_LIKELY_THEFT,
                    channel_id=config.NOTIFICATION_CHANNEL_LIKELY_THEFT_ALERT,
                    sound_name=config.NOTIFICATION_SOUND_LIKELY_THEFT_ALERT,
                )

        if validate_incident_request.customer_url:
            customer_obj = await customer_data_controller.get_by_customer_url(
                url=validate_incident_request.customer_url
            )

            if customer_obj is None:
                raise NotFoundException(
                    f"No such customer exists with this url: {validate_incident_request.customer_url}"
                )

            await incidents_controller.map_customer(
                incident_obj=incident_obj,
                customer_id=customer_obj.id,
                validate_incident_request=validate_incident_request,
            )

        return {"status": "success"}

    except NotFoundException as e:
        await error_logs_controller.register(
            {
                "incident_id": validate_incident_request.incident_id,
                "error_msg": str(e),
                "created_at": datetime.now(pytz.utc),
            }
        )
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"PATCH /incidents : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.put(
    "/comments",
    status_code=200,
    tags=["Incidents"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def edit_incident_comments(
    request: Request,
    edit_comments_request: EditIncidentCommentsRequest,
    audit_controller: IncidentsAuditController = Depends(
        controller_factory.get_audit_controller
    ),
):
    try:
        return await audit_controller.edit_comments(
            user_id=request.user.id,
            edit_comments_request=edit_comments_request,
        )

    except BadRequestException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"PUT /incidents/comments : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.get(
    "/{incident_id}",
    tags=["Incidents"],
    # dependencies=[Depends(AuthenticationRequired)],
)
async def get_incident_details(
    request: Request,
    incident_id: Annotated[int, Path(ge=1, le=9223372036854775807)],
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    audit_controller: IncidentsAuditController = Depends(
        controller_factory.get_audit_controller
    ),
    blacklist_controller: Incidents_Blacklist_Controller = Depends(
        controller_factory.get_blacklist_controller
    ),
    customer_data_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    customer_audit_controller: CustomersAuditController = Depends(
        controller_factory.get_customer_audit_controller
    ),
):
    try:
        return await incidents_controller.get_incident_details(
            incident_id=incident_id,
            audit_controller=audit_controller,
            blacklist_controller=blacklist_controller,
            customer_data_controller=customer_data_controller,
            customer_audit_controller=customer_audit_controller,
        )

    except BadRequestException as e:
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"GET /incidents/{incident_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.get(
    "/{incident_id}/evidences",
    tags=["Evidences"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_evidence_by_incident_id(
    incident_id: int,
    evidence_controller: EvidenceDataController = Depends(
        controller_factory.get_evidence_data_controller
    ),
):
    try:
        evidences = await evidence_controller.get_by_incident_id(incident_id)
        return {"evidences": evidences}
    except Exception as e:
        logger.error(f"GET /firebase/evidences/getEvidence/{incident_id} : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.post(
    "/{incident_id}/download",
    tags=["Incidents"],
    dependencies=[Depends(AuthenticationRequired)],
)
async def download_incident_video(
    incident_id: int,
    incident_contoller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
):
    try:
        incident = await incident_contoller.get_incident_by_id(incident_id)
        if incident.share_video_url:
            response = requests.get(incident.share_video_url)
            if response.ok:
                return {"share_video_url": incident.share_video_url}
            # return {"status": "failed", "message": "Video not found"}

        video_overlay = VideoLogoOverlay(incident.video_url)
        new_video_url = video_overlay.process_video()
        if new_video_url:
            await incident_contoller.update_incident_share_video_url(
                incident.id, new_video_url
            )
            return {"share_video_url": new_video_url}

        return {"status": "failed"}

    except Exception as e:
        logger.log_err_with_line(e)
        logger.error(f"GET /incidents/{incident_id}/download : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@incident_router.post(
    "/analyst/blacklist",
    status_code=200,
    tags=["Incidents"],
)
async def analyst_blacklist_test(
    background_tasks: BackgroundTasks,
    analyst_blacklist_incident_request: AnalystBlacklistIncidentRequest,
    audit_controller: IncidentsAuditController = Depends(
        controller_factory.get_audit_controller
    ),
    analyst_audit_controller: IncidentsAnalystAuditController = Depends(
        controller_factory.get_analyst_audit_controller
    ),
    blacklist_controller: Incidents_Blacklist_Controller = Depends(
        controller_factory.get_blacklist_controller
    ),
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
    cloudDB_controller: CloudDBController = Depends(
        controller_factory.get_cloudDB_controller
    ),
    customer_controller: CustomerDataController = Depends(
        controller_factory.get_customer_data_controller
    ),
    error_logs_controller: ErrorLogsController = Depends(
        controller_factory.get_error_logs_controller
    ),
):
    try:
        incident = await incidents_controller.analyst_blacklist(
            incident_id=analyst_blacklist_incident_request.id,
            blacklist_status=analyst_blacklist_incident_request.blacklist_status,
        )

        if analyst_blacklist_incident_request.blacklist_status:
            await analyst_audit_controller.register(
                {
                    "incident_id": incident.id,
                    "action_type": Incidents_Analyst_Audit.AnalystAuditAction.BLACKLISTED,
                    "status": Incidents_Analyst_Audit.AnalystAuditStatus.APPROVED,
                    "comments": analyst_blacklist_incident_request.comments,
                    "created_by": 1,
                    "created_at": datetime.now(pytz.utc),
                    "updated_at": datetime.now(pytz.utc),
                    "updated_by": 1,
                }
            )
            logger.info(f"incident {incident.id} added to watchlist")

            await audit_controller.register(
                {
                    "incident_id": incident.id,
                    "action_type": Incidents_Audit.AuditAction.BLACKLISTED,
                    "status": Incidents_Audit.AuditStatus.APPROVED,
                    "comments": analyst_blacklist_incident_request.comments,
                    "created_by": 1,
                    "created_at": datetime.now(pytz.utc),
                    "updated_at": datetime.now(pytz.utc),
                    "updated_by": 1,
                }
            )

            blacklist_obj = await blacklist_controller.get_by_incident_id(
                incident_id=incident.id
            )

            if blacklist_obj:
                if config.BLACKLIST_FIREBASE_ENABLED:
                    await cloudDB_controller.add_to_firebase_blacklist_collection(
                        blacklist_controller=blacklist_controller,
                        blacklist_id=blacklist_obj.id,
                        incident_obj=True,
                        customer_obj=False,
                    )

                if config.BLACKLIST_WEBSOCKET_ENABLED:
                    await BlacklistWebsocketService.push_to_blacklist(
                        blacklist_controller=blacklist_controller,
                        blacklist_id=blacklist_obj.id,
                        incident_obj=True,
                        customer_obj=False,
                    )
                    logger.info(f"incident {incident.id} added to watchlist")

        else:
            await incidents_controller.remove_from_blacklists(
                incident_id=incident.id,
                user_id=1,
            )

            await blacklist_controller.remove_from_blacklist(
                incident_id=incident.id,
            )

            await analyst_audit_controller.register(
                {
                    "incident_id": incident.id,
                    "action_type": Incidents_Analyst_Audit.AnalystAuditAction.BLACKLISTED,
                    "status": Incidents_Analyst_Audit.AnalystAuditStatus.APPROVED,
                    "comments": analyst_blacklist_incident_request.comments,
                    "created_by": 1,
                    "created_at": datetime.now(pytz.utc),
                    "updated_at": datetime.now(pytz.utc),
                    "updated_by": 1,
                }
            )

            await audit_controller.register(
                {
                    "incident_id": incident.id,
                    "action_type": Incidents_Audit.AuditAction.BLACKLISTED,
                    "status": Incidents_Audit.AuditStatus.DECLINED,
                    "comments": analyst_blacklist_incident_request.comments,
                    "created_by": 1,
                    "created_at": datetime.now(pytz.utc),
                    "updated_at": datetime.now(pytz.utc),
                    "updated_by": 1,
                }
            )

        return {"status": "success"}

    except BadRequestException as e:
        await error_logs_controller.register(
            {
                "incident_id": analyst_blacklist_incident_request.id,
                "error_msg": str(e),
                "created_at": datetime.now(pytz.utc),
            }
        )
        raise HTTPException(status_code=e.code, detail=e.message)

    except Exception as e:
        logger.error(f"GET /incidents/analyst/blacklist: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
