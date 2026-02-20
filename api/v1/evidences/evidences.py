from datetime import datetime

import pytz
from fastapi import APIRouter, Depends, HTTPException, Request
from jinja2 import Template

from app.controllers import EvidenceDataController, IncidentsController
from app.controllers.incidents import get_branch_name
from app.models import Evidence
from app.schemas.requests.incidents import BaseEvidenceRequest, CreateEvidenceRequest
from app.services import send_email
from core.exceptions import BadRequestException
from core.factory import Factory
from core.fastapi.dependencies.authentication import AuthenticationRequired
from core.library.logging import logger

evidence_router = APIRouter()

controller_factory = Factory()


async def shareEvidenceEmail(incident_obj, evidences_obj):
    with open("app/templates/evidencePack.html", "r", encoding="utf-8") as file:
        html_content = file.read()
        template = Template(html_content)
        msg_body = template.render(
            branch_name=await get_branch_name(incident_obj.branch_id),
            evidence_report_date=evidences_obj.created_at.strftime("%d %b %Y"),
            property_stolen=evidences_obj.property_details.get(
                "property_stolen", "N/A"
            ),
            property_value=evidences_obj.property_details.get("property_value", "N/A"),
            property_recovered=(
                "Yes" if evidences_obj.property_details.get("recovered") else "No"
            ),
            evidence_description=evidences_obj.evidence_description,
            video_url=incident_obj.video_url,
            theft_date=incident_obj.incident_time.strftime("%d/%m/%Y"),
            theft_time=incident_obj.incident_time.strftime("%H:%M %p"),
            share_email_id=evidences_obj.share_email_id,
            evidence_type=evidences_obj.evidence_type,
        )
        send_email(
            subject="Evidence Shared",
            recipient_email=evidences_obj.share_email_id,
            body=msg_body,
        )


@evidence_router.post("/", dependencies=[Depends(AuthenticationRequired)])
async def create_evidences(
    request: Request,
    evidence_data: CreateEvidenceRequest,
    evidence_controller: EvidenceDataController = Depends(
        controller_factory.get_evidence_data_controller
    ),
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
):
    try:
        incident = await incidents_controller.get_incident_by_id(
            evidence_data.incident_id
        )

        evidences_obj = await evidence_controller.register(
            {
                "incident_id": evidence_data.incident_id,
                "evidence_type": evidence_data.evidence_type,
                "property_details": (
                    {
                        "property_stolen": evidence_data.property_stolen,
                        "property_value": evidence_data.property_value,
                        "recovered": evidence_data.recovered,
                    }
                    if evidence_data.evidence_type == 1
                    else {}
                ),
                "evidence_description": evidence_data.evidence_description,
                "share_email_id": evidence_data.share_email_id,
                "created_by": request.user.id,
                "updated_by": request.user.id,
                "created_at": datetime.now(pytz.utc),
                "updated_at": datetime.now(pytz.utc),
            }
        )

        if (
            evidence_data.evidence_type == Evidence.EvidenceType.THEFT
            or evidence_data.evidence_type == Evidence.EvidenceType.NON_THEFT
        ):
            await shareEvidenceEmail(
                incident_obj=incident,
                evidences_obj=evidences_obj,
            )

        return {"status": "Evidence created", "evidence": evidences_obj}

    except BadRequestException:
        return {"message": "incident not found"}

    except Exception as e:
        logger.error(f"GET /firebase/incidents/start-listener : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@evidence_router.get("/{evidence_id}", dependencies=[Depends(AuthenticationRequired)])
async def get_evidence_by_id(
    evidence_id: int,
    evidence_controller: EvidenceDataController = Depends(
        controller_factory.get_evidence_data_controller
    ),
):
    try:
        evidence = await evidence_controller.get_by_id(evidence_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")
        return {"evidence": evidence}
    except Exception as e:
        logger.error(f"GET /firebase/evidences/{evidence_id} : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@evidence_router.put("/{evidence_id}", dependencies=[Depends(AuthenticationRequired)])
async def update_evidence(
    request: Request,
    evidence_id: int,
    evidence_data: BaseEvidenceRequest,
    evidence_controller: EvidenceDataController = Depends(
        controller_factory.get_evidence_data_controller
    ),
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
):
    try:
        # Build update payload
        update_payload = {
            "evidence_type": evidence_data.evidence_type,
            "property_details": (
                {
                    "property_stolen": evidence_data.property_stolen,
                    "property_value": evidence_data.property_value,
                    "recovered": evidence_data.recovered,
                }
                if evidence_data.evidence_type == 1
                else {}
            ),
            "evidence_description": evidence_data.evidence_description,
            "share_email_id": evidence_data.share_email_id,
            "updated_at": datetime.now(pytz.utc),
            "updated_by": request.user.id,
        }

        # Delegate the update to the controller
        updated_evidence = await evidence_controller.evidence_update(
            evidence_id, update_payload
        )

        if (
            updated_evidence.evidence_type == Evidence.EvidenceType.THEFT
            or evidence_data.evidence_type == Evidence.EvidenceType.NON_THEFT
        ):
            incident = await incidents_controller.get_incident_by_id(
                updated_evidence.incident_id
            )
            await shareEvidenceEmail(
                incident_obj=incident,
                evidences_obj=updated_evidence,
            )

        return {"status": "Evidence updated", "evidence": updated_evidence}

    except Exception as e:
        logger.error(f"PUT /firebase/evidences/{evidence_id} : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@evidence_router.post("/{evidence_id}", dependencies=[Depends(AuthenticationRequired)])
async def reshareEvidence(
    request: Request,
    evidence_id: int,
    evidence_controller: EvidenceDataController = Depends(
        controller_factory.get_evidence_data_controller
    ),
    incidents_controller: IncidentsController = Depends(
        controller_factory.get_incidents_controller
    ),
):
    try:
        evidence = await evidence_controller.get_by_id(evidence_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")

        if (
            evidence.evidence_type == Evidence.EvidenceType.THEFT
            or evidence.evidence_type == Evidence.EvidenceType.NON_THEFT
        ):
            incident = await incidents_controller.get_incident_by_id(
                evidence.incident_id
            )
            await shareEvidenceEmail(
                incident_obj=incident,
                evidences_obj=evidence,
            )

        return {"status": "success", "evidence": evidence}
    except Exception as e:
        logger.error(f"POST /firebase/evidences/{evidence_id}/reshare : {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
