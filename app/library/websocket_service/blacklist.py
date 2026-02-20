import json

from app.controllers.blacklist_sent_logs import BlacklistSentLogsController
from app.controllers.customer_blacklist import Customers_Blacklist_Controller
from app.controllers.incidents_blacklist import Incidents_Blacklist_Controller
from app.library.entity_service import entity
from app.library.helpers import get_blacklist_data
from app.library.helpers.entity_helper import get_company_branch_id_by_uuid
from app.models.incidents import BlacklistSentLogs
from core.cache import Cache
from core.cache.redis_backend import RedisBackend
from core.library.logging import logger


class BlacklistWebsocketService:
    @staticmethod
    async def remove_from_blacklist(
        branch_id: int,
        blacklist_sent_logs_controller: BlacklistSentLogsController,
        company_id: int,
        blacklist_id: int,
        customer_uuid_id: str,
        incident_int_id: int | None = None,
        incident_id: str | None = None,
        customer_id: str | None = None,
    ):
        branches = await Cache.get_all_branches()

        if branches and branch_id in branches:
            branch_uuid = branches[branch_id]
        else:
            branch_uuid = await entity.get_branch_uuid(branch_id)
            if branch_uuid is None:
                logger.error(f"Error in getting branch uuid: {branch_id}")
                return
        
        await blacklist_sent_logs_controller.register(
            {
                "company_id": company_id,
                "branch_id": branch_id,
                "blacklist_id":blacklist_id,
                "customer_id":customer_id,
                "incident_id": incident_int_id,
                "action_type": BlacklistSentLogs.ActionTypes.REMOVE,
            }
        )

        # 🔹 Websocket message
        message = json.dumps(
            {
                "action": "remove",
                "data": {
                    "customer_id": customer_uuid_id,
                    "incident_id": incident_id,
                },
            }
        )

        redis_channel = f"channel_branch_{branch_uuid}"
        redis_backend = RedisBackend()
        await redis_backend.publish(channel=redis_channel, message=message)

        

    @staticmethod
    async def push_to_blacklist(
        blacklist_sent_logs_controller: BlacklistSentLogsController,
        blacklist_controller: Incidents_Blacklist_Controller
        | Customers_Blacklist_Controller,
        blacklist_id: int,
        incident_obj: bool,
        customer_obj: bool,
    ):
        blacklist_data = await get_blacklist_data(
            blacklist_controller=blacklist_controller,
            blacklist_id=blacklist_id,
            incident_obj=incident_obj,
            customer_obj=customer_obj,
        )

        branch_uuid = blacklist_data["branch_id"]
        company_id = blacklist_data["company_id"]
        branch_id = blacklist_data["branch_id"]
        company_id_as_int,branch_id_as_int=await get_company_branch_id_by_uuid(company_id, branch_id)
        customer_int_id = blacklist_data["customer_int_id"]
        id=blacklist_data.get("id")   
        
        await blacklist_sent_logs_controller.register(
            {
                "company_id": company_id_as_int,
                "branch_id": branch_id_as_int,
                "customer_id": customer_int_id,
                "incident_id": id,
                "blacklist_id": blacklist_id,
                "action_type": BlacklistSentLogs.ActionTypes.ADD,
            }
        )     

        # 🔹 Websocket message
        message = json.dumps(
            {
                "action": "add",
                "data": blacklist_data,
            }
        )

        redis_channel = f"channel_branch_{branch_uuid}"
        redis_backend = RedisBackend()
        await redis_backend.publish(channel=redis_channel, message=message)
        
        
