from app.library.entity_service import entity
from core.cache import Cache
from core.library.logging import logger

async def get_camera_id_by_uuid(camera_uuid: str) -> int:
    if camera_uuid is None:
        return None

    camera_id = await Cache.get_camera_id(camera_uuid)

    if camera_id:
        return camera_id

    return await entity.get_camera_by_uuid(camera_uuid)


async def get_company_id_by_uuid(company_uuid: str) -> int:
    company_info = await Cache.get_company_id(company_uuid)

    if company_info:
        return company_info["company_id"]

async def get_branch_id_by_uuid(branch_uuid: str) -> int:
    branch_info = await Cache.get_company_id(branch_uuid)

    if branch_info:
        return branch_info["branch_id"]


async def get_company_branch_id_by_uuid(company_uuid: str, branch_uuid: str) -> int:
    company_id = await get_company_id_by_uuid(company_uuid)
    branch_id = await get_branch_id_by_uuid(branch_uuid)

    if company_id is None or branch_id is None:
        return {
            "company_id": company_id,
            "branch_id": branch_id,
        }

    company_branch_id = {
        "company_id": company_uuid,
        "branch_id": branch_uuid,
    }
    company_branch_response = await entity.get_company_branch_id(company_branch_id)
    
    if company_branch_response is None:
        logger.error("Error in getting company or branch")
        return
        
    company_id = company_branch_response.get("company_id")
    branch_id = company_branch_response.get("branch_id")
    
    return company_id,branch_id
    
async def get_company_branch_camera_id(
    company_uuid: str, branch_uuid: str, camera_uuid: str
):
    company_id = await get_company_id_by_uuid(company_uuid)
    branch_id = await get_branch_id_by_uuid(branch_uuid)
    camera_id = await get_camera_id_by_uuid(camera_uuid)

    if company_id and branch_id and camera_id:
        return company_id, branch_id, camera_id

    if company_id is None or branch_id is None:
        company_branch_id = {
            "company_id": company_uuid,
            "branch_id": branch_uuid,
        }
        company_branch_response = await entity.get_company_branch_id(company_branch_id)

        if company_branch_response is None:
            logger.error(f"Company or branch not found - company_uuid: {company_uuid}, branch_uuid: {branch_uuid}")
            return None, None, None

        company_id = company_branch_response.get("company_id")
        branch_id = company_branch_response.get("branch_id")

    if camera_id is None and camera_uuid is not None:
        camera_details = {
            "camera_id": camera_uuid,
            "company_id": company_id,
            "branch_id": branch_id,
        }
        camera_response = await entity.create_camera_details(camera_details)
        logger.info(camera_response)
        camera_id = camera_response.get("id")

    return company_id, branch_id, camera_id
