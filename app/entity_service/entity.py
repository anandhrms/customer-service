import os

import requests

from core.cache import Cache
from core.library.logging import logger


class EntityService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EntityService, cls).__new__(cls)
        return cls._instance

    def __init__(self, url: str, headers: dict, login_request: dict):
        if not hasattr(self, "_initialized"):
            self.url = url
            self.headers = headers
            self.login_request = login_request
            self._initialized = True

    async def get_profile(self, user_id: int):
        """
        Get Profile response from Entity Service

        user_id: User id \n
        """
        auth_token = await self.login()

        self.headers["Authorization"] = f"Bearer {auth_token}"
        try:
            user_profile = await Cache.get_user_profile(user_id)
            if user_profile:
                return user_profile

            profile_response = requests.get(
                url=f"{self.url}/v1/users/profile/{user_id}",
                headers=self.headers,
                timeout=5,
            ).json()

            await Cache.cache_user_profile(user_id, profile_response)

            return profile_response

        except Exception as e:
            logger.error(f"Error /users/{user_id} : {str(e)}")
            raise e

    async def login(self) -> str:
        """
        Login to Entity service
        """
        try:
            auth_token = await Cache.get_entity_auth_token()
            if auth_token:
                return auth_token

            login_response = requests.post(
                url=f"{self.url}/v1/users/login",
                headers=self.headers,
                timeout=5,
                json=self.login_request,
            ).json()
            auth_token = login_response.get("access_token")

            await Cache.cache_entity_auth_token(auth_token)

            return auth_token

        except Exception as e:
            logger.error(f"Error /users/login : {str(e)}")
            raise e

    async def get_hardware_status(self, branch_ids: list[int]):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            params = {"branch_ids": branch_ids}
            hardware_status_response = requests.get(
                url=f"{self.url}/v1/hardwares/status",
                headers=self.headers,
                params=params,
                timeout=5,
            ).json()

            return hardware_status_response

        except Exception as e:
            logger.error(f"Error /hardwares/status : {str(e)}")
            return {}

    async def get_camera_status(self, branch_ids: list[int]):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            params = {"branch_ids": branch_ids}
            camera_status_response = requests.get(
                url=f"{self.url}/v1/cameras/status",
                headers=self.headers,
                params=params,
                timeout=5,
            ).json()

            return camera_status_response

        except Exception as e:
            logger.error(f"Error /cameras/status : {str(e)}")
            return {}

    async def get_branch_users(
        self,
        branch_id: int,
    ):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            branch_users_response = requests.get(
                url=f"{self.url}/v1/users/branches/{branch_id}",
                headers=self.headers,
                timeout=5,
            ).json()

            return branch_users_response

        except Exception as e:
            logger.error(f"Error /branches/{branch_id} : {str(e)}")
            raise e

    async def delete_fcm_token(
        self,
        token: str,
    ):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            json_data = {
                "token": token,
            }

            delete_token_response = requests.delete(
                url=f"{self.url}/v1/users/fcm-tokens",
                headers=self.headers,
                timeout=5,
                json=json_data,
            ).json()

            return delete_token_response

        except Exception as e:
            logger.error(f"Error /users/fcm-tokens : {str(e)}")
            raise e

    async def create_notification(
        self,
        branch_id: int,
        template: str,
        group: int,
        incident_id: int,
        notification_group_type: str,
    ):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"
            json_data = {
                "branch_id": branch_id,
                "template": template,
                "group": group,
                "incident_id": incident_id,
                "notification_group_type": notification_group_type,
            }
            notification_response = requests.post(
                url=f"{self.url}/v1/notifications/",
                headers=self.headers,
                timeout=5,
                json=json_data,
            ).json()

            return notification_response

        except Exception as e:
            logger.error(f"Error /notifications : {str(e)}")
            raise e

    async def get_fcm_token(
        self,
        branch_id: int,
        notification_group_type: str,
        notification_type: str | None = None,
        except_user_ids: list[int] | None = None,
    ) -> list:
        """
        Get FCM token of all users of the branch from Entity Service
        branch_id: User id \n
        auth_token: Authorization Token
        """
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"
            params = {
                "notification_group_type": notification_group_type,
                "notification_type": notification_type,
            }
            if except_user_ids:
                params["except_user_ids"] = except_user_ids

            fcm_token = requests.get(
                url=f"{self.url}/v1/notifications/fcm/token/branches/{branch_id}",
                headers=self.headers,
                params=params,
                timeout=5,
            ).json()
            return fcm_token.get("token")

        except Exception as e:
            logger.error(
                f"Error /notifications/fcm/token/branches/{branch_id} : {str(e)}"
            )
            raise e

    async def create_camera_details(self, create_camera_request: dict):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            response = requests.post(
                url=f"{self.url}/v1/cameras/",
                headers=self.headers,
                timeout=5,
                json=create_camera_request,
            ).json()

            return response

        except Exception as e:
            logger.error(f"Error /cameras/ : {str(e)}")
            raise e

    async def create_camera_incidents(self, create_camera_incident_request: dict):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            requests.post(
                url=f"{self.url}/v1/cameras/incidents",
                headers=self.headers,
                timeout=5,
                json=create_camera_incident_request,
            ).json()

        except Exception as e:
            logger.error(f"Error /cameras/incidents : {str(e)}")
            raise e

    async def get_company_uuid(self, company_id: int):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            response = requests.get(
                url=f"{self.url}/v1/companies/{company_id}",
                headers=headers,
                timeout=5,
            )

            if response.ok:
                response_data = response.json()
                await Cache.cache_company(
                    company_id=company_id,
                    company_uuid=response_data.get("uuid"),
                )
                return response_data.get("uuid")

        except Exception as e:
            logger.error(f"Error /companies/{company_id} : {str(e)}")
            raise e

    async def get_branch_info(self, branch_id: int):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            response = requests.get(
                url=f"{self.url}/v1/branches/{branch_id}",
                headers=headers,
                timeout=5,
            )

            if response.ok:
                response_data = response.json()
                return response_data

        except Exception as e:
            logger.error(f"Error /branches/{branch_id} : {str(e)}")
            raise e

    async def get_branch_uuid(self, branch_id: int):
        try:
            branch_info = await self.get_branch_info(branch_id)

            if branch_info:
                await Cache.cache_branch(
                    branch_id=branch_id,
                    branch_uuid=branch_info.get("uuid"),
                )
                return branch_info.get("uuid")

        except Exception as e:
            logger.error(f"Error /branches/{branch_id} : {str(e)}")
            raise e

    async def get_branch_timezone(self, branch_id: int):
        try:
            branch_info = await self.get_branch_info(branch_id)

            if branch_info:
                await Cache.cache_branch_timezone(
                    branch_id=branch_id,
                    branch_timezone=branch_info.get("timezone"),
                )
                return branch_info.get("timezone")

        except Exception as e:
            logger.error(f"Error /branches/{branch_id} : {str(e)}")
            raise e

    async def get_branch_name(self, branch_id: int):
        try:
            branch_info = await self.get_branch_info(branch_id)

            if branch_info:
                await Cache.cache_branch_name(
                    branch_id=branch_id,
                    branch_name=branch_info.get("name"),
                )
                return branch_info.get("name")

        except Exception as e:
            logger.error(f"Error /branches/{branch_id} : {str(e)}")
            raise e

    async def get_camera_by_uuid(self, camera_uuid: str) -> int:
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            params = {"camera_id": camera_uuid}
            response = requests.get(
                url=f"{self.url}/v1/cameras/",
                headers=headers,
                timeout=5,
                params=params,
            )

            if response.ok:
                response_data = response.json()
                if response_data:
                    await Cache.cache_camera_id(
                        camera_uuid=camera_uuid,
                        camera_id=response_data.get("id"),
                    )
                    return response_data.get("id")

        except Exception as e:
            logger.error(f"Error /cameras/ : {str(e)}")
            raise e

    async def get_company_branch_id(self, company_branch_id: dict):
        try:
            auth_token = await self.login()
            self.headers["Authorization"] = f"Bearer {auth_token}"

            response = requests.get(
                url=f"{self.url}/v1/companies/branches",
                headers=headers,
                timeout=5,
                params=company_branch_id,
            )

            if response.ok:
                response_data = response.json()
                branch_info = {
                    "branch_id": response_data.get("branch_id"),
                    "branch_name": response_data.get("branch_name"),
                }
                await Cache.cache_branch_id(
                    branch_uuid=company_branch_id.get("branch_id"),
                    branch_info=branch_info,
                )

                company_info = {
                    "company_id": response_data.get("company_id"),
                    "company_name": response_data.get("company_name"),
                }
                await Cache.cache_company_id(
                    company_uuid=company_branch_id.get("company_id"),
                    company_info=company_info,
                )

                return response_data

            logger.error(f"Error /companies/branches : {response.json()}")
            return None

        except Exception as e:
            logger.error(f"Error /companies/branches : {str(e)}")
            return None


ENTITY_SERVICE_URL = os.getenv("ENTITY_SERVICE_URL")
ENTITY_LOGIN_EMAIL = os.getenv("ENTITY_LOGIN_EMAIL")
ENTITY_LOGIN_PASSWORD = os.getenv("ENTITY_LOGIN_PASSWORD")

login_request = {"email": ENTITY_LOGIN_EMAIL, "password": ENTITY_LOGIN_PASSWORD}
headers = {"Content-Type": "application/json"}

entity = EntityService(
    ENTITY_SERVICE_URL,
    headers,
    login_request,
)
