import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from jose import JWTError, jwt
from redis.asyncio.client import PubSub
from starlette.websockets import WebSocketDisconnect, WebSocketState

from core.cache import Cache
from core.cache.redis_backend import RedisBackend
from core.config import config
from core.exceptions import UnauthorizedException
from core.library.logging import logger

ws_router = APIRouter()

active_websockets = set()

# only one connection per store
branch_websockets = {}


async def validate_token(token: str):
    try:
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
        )
        user_id = payload.get("user_id")

    except JWTError:
        raise UnauthorizedException("Invalid token")

    is_blacklisted = await Cache.is_token_blacklisted(token)
    if is_blacklisted:
        raise UnauthorizedException("Invalid token")

    return user_id


async def listen_for_messages(pubsub: PubSub, websocket: WebSocket):
    while True:
        if websocket.client_state == WebSocketState.DISCONNECTED:
            break

        message = await pubsub.get_message()
        if message and message["type"] == "message":
            try:
                await websocket.send_text(message["data"].decode("utf-8"))

            except WebSocketDisconnect:
                break

            except Exception:
                break

        await asyncio.sleep(0.1)


@ws_router.websocket("/ws")
async def websocket_endpoint(
    user_id: Annotated[int, Depends(validate_token)],
    websocket: WebSocket,
):
    redis_channel = f"channel_{user_id}"
    await websocket.accept()

    active_websockets.add(websocket)

    try:
        redis_backend = RedisBackend()
        pubsub = await redis_backend.subscribe(redis_channel)

        asyncio.create_task(listen_for_messages(pubsub, websocket))

        while True:
            await asyncio.sleep(1)

    except UnauthorizedException:
        return HTTPException(status_code=401, detail="Unauthorized")

    except WebSocketDisconnect:
        logger.info("disconnected")

    except Exception as e:
        logger.error(f"server error: {str(e)}")

    except RuntimeError as e:
        logger.error(f"server error: {str(e)}")

    finally:
        try:
            if len(active_websockets) == 1:
                await redis_backend.unsubscribe(pubsub, redis_channel)
            await websocket.close()
            active_websockets.remove(websocket)

        except Exception:
            active_websockets.clear()


@ws_router.websocket("/ws/branches")
async def branch_websocket_connection(
    branch_id: str,
    websocket: WebSocket,
):
    # TODO: Implement whether branch_id exists

    redis_channel = f"channel_branch_{branch_id}"
    await websocket.accept()

    branch_websockets[branch_id] = websocket

    try:
        redis_backend = RedisBackend()
        pubsub = await redis_backend.subscribe(redis_channel)

        asyncio.create_task(listen_for_messages(pubsub, websocket))

        while True:
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info("disconnected")

    except Exception as e:
        logger.error(f"server error: {str(e)}")

    except RuntimeError as e:
        logger.error(f"server error: {str(e)}")

    finally:
        try:
            await redis_backend.unsubscribe(pubsub, redis_channel)
            await websocket.close()
            del branch_websockets[branch_id]

        except Exception:
            branch_websockets.clear()
