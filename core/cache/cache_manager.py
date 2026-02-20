from functools import partial, wraps
from typing import Type

from .base import BaseBackend, BaseKeyMaker
from .cache_tag import CacheTag
from .redis_backend import RedisBackend


class CacheManager:
    def __init__(self, backend: Type[BaseBackend] = None):
        self.backend = backend
        self.key_maker = None

    def init(self, backend: Type[BaseBackend], key_maker: Type[BaseKeyMaker]) -> None:
        self.backend = backend
        self.key_maker = key_maker

    def cached(self, prefix: str = None, tag: CacheTag = None, ttl: int = 60):
        def _cached(function):
            @wraps(function)
            async def __cached(*args, **kwargs):
                if not self.backend or not self.key_maker:
                    raise ValueError("Backend or KeyMaker not initialized")

                key = await self.key_maker.make(
                    function=function,
                    prefix=prefix if prefix else tag.value,
                )
                cached_response = await self.backend.get(key=key)
                if cached_response:
                    return cached_response

                response = await function(*args, **kwargs)
                await self.backend.set(response=response, key=key, ttl=ttl)
                return response

            return __cached

        return _cached

    async def get_company_id(self, company_uuid: str) -> str | None:
        """
        Get company id from cache
        """
        return await self.backend.get(key=company_uuid)

    async def get_branch_id(self, branch_uuid: str) -> str | None:
        """
        Get branch id from cache
        """
        return await self.backend.get(key=branch_uuid)

    async def get_camera_id(self, camera_uuid: str) -> str | None:
        """
        Get camera id from cache
        """
        return await self.backend.get(key=camera_uuid)

    async def cache_company_id(self, company_uuid: str, company_info: dict) -> None:
        """
        Caching the company info
        """
        await self.backend.set(response=company_info, key=company_uuid, ttl=86400)
        await self.cache_company(
            company_uuid=company_uuid, company_id=company_info.get("company_id")
        )

    async def cache_branch_id(self, branch_uuid: str, branch_info: dict) -> None:
        """
        Caching the branch info
        """
        await self.backend.set(response=branch_info, key=branch_uuid, ttl=86400)
        await self.cache_branch(
            branch_uuid=branch_uuid, branch_id=branch_info.get("branch_id")
        )

    async def cache_camera_id(self, camera_uuid: str, camera_id: int) -> None:
        """
        Caching the camera id
        """
        await self.backend.set(response=camera_id, key=camera_uuid, ttl=86400)

    async def cache_company(self, company_id: int, company_uuid: str):
        """
        Cache all company ids
        """
        companies = await self.get_all_companies()
        if companies is None:
            companies = {}

        companies[company_id] = company_uuid

        await self.backend.set(response=companies, key="companies", ttl=86400)

    async def cache_branch(self, branch_id: int, branch_uuid: str):
        """
        Cache all branch ids
        """
        branches = await self.get_all_branches()
        if branches is None:
            branches = {}

        branches[branch_id] = branch_uuid

        await self.backend.set(response=branches, key="branches", ttl=86400)

    async def cache_branch_timezone(self, branch_id: int, branch_timezone: str):
        """
        Cache all branch timezone
        """
        branches = await self.get_all_branches_timezone()
        if branches is None:
            branches = {}

        branches[branch_id] = branch_timezone

        await self.backend.set(response=branches, key="branch_timezone", ttl=86400)

    async def cache_branch_name(self, branch_id: int, branch_name: str):
        """
        Cache all branch names
        """
        branches = await self.get_all_branch_name()
        if branches is None:
            branches = {}

        branches[branch_id] = branch_name

        await self.backend.set(response=branches, key="branch_name", ttl=86400)

    async def get_branch_timezone(self, branch_id: int):
        """
        Get timezone of the branch
        """
        branch_timezone = await self.backend.get(key="branch_timezone")

        if branch_timezone is None:
            return None

        if str(branch_id) not in branch_timezone:
            return None

        return branch_timezone[str(branch_id)]

    async def get_branch_name(self, branch_id: int):
        """
        Get name of the branch
        """
        branch_name = await self.backend.get(key="branch_name")

        if branch_name is None:
            return None

        if str(branch_id) not in branch_name:
            return None

        return branch_name[str(branch_id)]

    async def get_all_branches_timezone(self) -> dict | None:
        """
        Get all branches
        """
        return await self.backend.get(key="branch_timezone")

    async def get_all_branch_name(self) -> dict | None:
        """
        Get all branch name
        """
        return await self.backend.get(key="branch_name")

    async def get_all_companies(self) -> dict | None:
        """
        Get all compaines
        """
        return await self.backend.get(key="companies")

    async def get_all_branches(self) -> dict | None:
        """
        Get all branches
        """
        return await self.backend.get(key="branches")

    async def is_token_blacklisted(self, token: str) -> str | None:
        """
        Check if auth token is blacklisted
        """
        return await self.backend.get(key=token)

    async def cache_entity_auth_token(self, auth_token: str) -> None:
        """
        Caching entity service auth token
        """
        await self.backend.set(response=auth_token, key="entity_auth_token", ttl=86400)

    async def get_entity_auth_token(self) -> str | None:
        """
        Get entity auth token
        """
        return await self.backend.get(key="entity_auth_token")

    async def cache_user_profile(self, user_id: int, user_profile: dict):
        """
        Caching user profile
        """
        users = await self.backend.get(key="users")

        if users is None:
            users = {}

        users[user_id] = user_profile
        await self.backend.set(response=users, key="users", ttl=86400)

    async def get_user_profile(self, user_id: int) -> dict | None:
        """
        Get user profile
        """
        users = await self.backend.get(key="users")
        if users is None:
            return None

        user_profile = users.get(str(user_id))

        return user_profile

    async def remove_by_tag(self, tag: CacheTag) -> None:
        await self.backend.delete_startswith(value=tag.value)

    async def remove_by_prefix(self, prefix: str) -> None:
        await self.backend.delete_startswith(value=prefix)


redis_backend = partial(RedisBackend)

Cache = CacheManager(redis_backend)
