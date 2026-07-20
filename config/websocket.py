import asyncio
import json
import logging
from urllib.parse import parse_qs
from django.conf import settings
from asgiref.sync import sync_to_async
import redis.asyncio as aioredis
import redis

logger = logging.getLogger(__name__)

# Registry of connected websockets: user_id -> set of send callables
_connections = {}
_registry_lock = asyncio.Lock()
_redis_listener_task = None

async def register_connection(user_id, send):
    async with _registry_lock:
        if user_id not in _connections:
            _connections[user_id] = set()
        _connections[user_id].add(send)
        logger.info(f"Registered connection for user {user_id}. Total active users: {len(_connections)}")

async def unregister_connection(user_id, send):
    async with _registry_lock:
        if user_id in _connections:
            _connections[user_id].discard(send)
            if not _connections[user_id]:
                del _connections[user_id]
        logger.info(f"Unregistered connection for user {user_id}. Total active users: {len(_connections)}")

async def broadcast_to_user(user_id, message_dict):
    async with _registry_lock:
        sends = _connections.get(user_id, set()).copy()
    if sends:
        payload = json.dumps(message_dict)
        logger.info(f"Broadcasting message to user {user_id} with {len(sends)} active connections")
        for send in sends:
            try:
                await send({
                    "type": "websocket.send",
                    "text": payload
                })
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")

def publish_notification(user_id, payload):
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.publish("zigzag_notifications", json.dumps({
            "user_id": user_id,
            "payload": payload
        }))
        logger.info(f"Published notification to Redis Pub/Sub for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to publish notification to Redis for user {user_id}: {e}")

async def start_redis_listener():
    global _redis_listener_task
    if _redis_listener_task is None:
        _redis_listener_task = asyncio.create_task(redis_pubsub_listener())

async def redis_pubsub_listener():
    logger.info("Starting Redis Pub/Sub listener...")
    while True:
        try:
            r = aioredis.from_url(settings.REDIS_URL)
            pubsub = r.pubsub()
            await pubsub.subscribe("zigzag_notifications")
            logger.info("Subscribed to Redis channel 'zigzag_notifications'")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        user_id = data.get("user_id")
                        payload = data.get("payload")
                        if user_id:
                            await broadcast_to_user(user_id, payload)
                    except Exception as e:
                        logger.error(f"Error parsing Redis message: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Redis connection error in Pub/Sub: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

@sync_to_async
def get_user_from_token(token_str):
    from rest_framework_simplejwt.tokens import AccessToken
    from apps.accounts.models import User
    try:
        access_token = AccessToken(token_str)
        user_id = access_token["user_id"]
        return User.objects.filter(id=user_id, is_active=True).first()
    except Exception:
        return None

@sync_to_async
def get_unread_count(user):
    from apps.notifications.models import Notification
    return Notification.objects.filter(recipient=user, is_read=False).count()

async def handle_websocket(scope, receive, send):
    query_string = scope.get("query_string", b"").decode("utf-8")
    query_params = parse_qs(query_string)
    token = query_params.get("token", [None])[0]

    if not token:
        await send({"type": "websocket.close", "code": 4001})
        return

    user = await get_user_from_token(token)
    if not user:
        await send({"type": "websocket.close", "code": 4002})
        return

    user_id = user.id
    await send({"type": "websocket.accept"})
    await register_connection(user_id, send)

    # Send initial unread count right after connection
    unread_count = await get_unread_count(user)
    await send({
        "type": "websocket.send",
        "text": json.dumps({
            "type": "unread_count",
            "count": unread_count
        })
    })

    try:
        while True:
            message = await receive()
            if message["type"] == "websocket.disconnect":
                break
    finally:
        await unregister_connection(user_id, send)
