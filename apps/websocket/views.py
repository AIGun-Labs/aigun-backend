import json
import uuid
import asyncio
import settings
from middleware.lifespan import on_startup
from middleware.security import RS256Checker
from fastapi.websockets import WebSocket
from typing import Awaitable, Callable, Any, Optional, List
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, ValidationError

from data import Context
from uuid import UUID
from uuid6 import uuid7
from apps.websocket import models

from apps.websocket.models import WebSocketRequest, WebSocketMessage
from apps.websocket import services
from apps.user import schemas as user_schemas
from apps.user import services as user_services
from views.render import JsonResponseEncoder

from data.logger import create_logger
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import select



logger = create_logger('dogex-intelligence-ws')
ws = APIRouter(prefix='/ws/v1')


def context_from_websocket(websocket: WebSocket) -> Context:
    """
    Get context from WebSocket connection
    :param websocket: WebSocket connection object
    :return: Context object
    """
    return websocket.app.state.context


def checker_from_websocket(websocket: WebSocket) -> RS256Checker:
    """
    Get JWT checker from WebSocket connection
    :param websocket: WebSocket connection object
    :return: JWT checker object
    """
    return websocket.app.state.checker


# Create async lock
groups_lock = asyncio.Lock()


# Subscription set for saving connections and distributing messages
class SubscriptionGroup:
    def __init__(self):
        # self.tag_ids = []
        # self.websockets: Dict[str, WebSocket] = {}
        # self.users: set[str] = set()
        # self.tags : Dict[str,set[str]] = {}
        self.subweb: dict[str, set[WebSocket]] = {}  # Save relationship between subscription set and websocket
        self.sub: dict[str, set[str]] = {}  # Save relationship between words and subscription sets
        # self.count = 0

    def add_tags(self, tag: str, user_id: str):
        """
        Add subscription tags
        :param tags: Subscription tag list
        """
        if tag not in self.tags:
            self.tags[tag] = [user_id]
        else:
            self.tags[tag].append(user_id)

    def add_tag_ids(self, tag_ids: list[str]):
        """
        Add a tag_id
        :param tag_ids: tag_id
        """
        self.tag_ids.extend(tag_ids)

    def add_users(self, user_id: str):
        """
        Add a user id to subscription set
        :param user_id: User id
        """
        self.users.add(user_id)

    def remove_users(self, user_id: str):
        """
        Remove a user id from subscription set
        :param user_id: User id
        """
        self.users.discard(user_id)

    def remove_tags_user(self, user_id: str):
        """
        Remove a user id from tags dictionary
        :param user_id: User id
        """
        for tag, users in self.tags.items():
            if user_id in users:
                users.remove(user_id)

    def add_websocket(self, websocket: WebSocket, user_id: str):
        """
        Add a WebSocket connection to subscription set
        :param user_id: Connection key
        :param websocket: WebSocket connection object
        """
        self.websockets[user_id] = websocket

    def add_subweb(self, sub_id: str, websocket: WebSocket):
        """
        Add a WebSocket connection to subscription set
        :param sub_id: Connection key
        :param websocket: WebSocket connection object
        """
        if sub_id not in self.subweb:
            logger.info(f"New subscription set {sub_id}, websocket")
            self.subweb[sub_id] = set()

        self.subweb[sub_id].add(websocket)

    def remove_subweb(self, sub_id: str, websocket: WebSocket):
        """
        Remove a WebSocket connection from subweb
        :param sub_id: Connection key
        :param websocket: WebSocket connection object
        """
        if sub_id in self.subweb:
            self.subweb[sub_id].discard(websocket)

    def remove_sub(self, sub_id: str):
        """
        Remove a subscription from subscription set
        :param sub_id: Subscription key
        """
        if sub_id in self.subweb:
            del self.subweb[sub_id]

    # Send message to all users in subscription set
    async def send_message(self, message: Any, sub_word: set[str | Any]):
        """
        Send message to all users in subscription set
        :param message: Message to send
        :sub_word: tags
        """
        # Combine the information to be sent into a dictionary
        response_data = {
            "type": "message",
            "data": message
        }
        # Pre-serialize once to avoid repeated serialization
        try:
            payload = json.dumps(response_data, ensure_ascii=False, cls=JsonResponseEncoder)
        except Exception as e:
            logger.error(f"Error serializing message: {e}", exc_info=True)
            return
        logger.info(f"Subscription set: {self.sub}")
        # Find all subscription sets that should be pushed based on intelligence tags
        uuid_set = set()
        for key in sub_word:
            current_set = self.sub.get(key, set())  # tag: subscription set
            logger.info(f"Intelligence tag: {key}, corresponding subscription set: {current_set}")
            uuid_set |= current_set
        logger.info(f"Intelligence corresponding subscription set: {uuid_set}")
        # Find all websocket objects based on subscription set
        websocket_set = set()
        for sub_id in uuid_set:
            websockets = self.subweb.get(sub_id, set())
            websocket_set |= websockets
        logger.info(f"Push intelligence to subscription set: {websocket_set}, corresponding websocket count: {len(websocket_set)}")

        cleanup_websockets = []

        async def _safe_send(ws: WebSocket, text: str):
            try:
                if 1 == ws.client_state.value:
                    await ws.send({"type": "websocket.send", "text": text})
                    # await websocket.send_json(response_data)
                else:
                    # Clean up all references to this websocket in subscription sets
                    cleanup_websockets.append(ws)
                    # async with groups_lock:
                    #     for _sid, _set in list(self.subweb.items()):
                    #         _set.discard(ws)
            except WebSocketDisconnect:
                # Clean up disconnected websocket references
                async with groups_lock:
                    # for _sid, _set in list(self.subweb.items()):
                    #     _set.discard(ws)
                    cleanup_websockets.append(ws)
                logger.error("WebSocket disconnected during send", exc_info=True)
            except Exception as e:
                logger.error(f"Error sending message to user: {e}", exc_info=True)

        await asyncio.gather(*[_safe_send(ws, payload) for ws in websocket_set], return_exceptions=True)

        # Batch clean up invalid websocket connections
        if cleanup_websockets:
            async with groups_lock:
                for ws in cleanup_websockets:
                    for _sid, _set in list(self.subweb.items()):
                        _set.discard(ws)


global_subscription = SubscriptionGroup()



# Polling time slot
TIME_WHEEL_SIZE = 300
WS_VIEW = Callable[[WebSocket, WebSocketRequest], Awaitable[None]]


class WebSocketRoomState(BaseModel):
    user_id: Optional[str | UUID] = None  # User ID
    time_index: int  # Current time wheel slot index
    sub_ids: list  # New user subscription set ID storage
    configs: dict[str, Any] = {}


class WebSocketRoom:
    """
    WebSocket room layer manager (will hook WebSocket lifecycle, only execute decorated view function after receiving message)
    """
    time_wheel_locks: list[asyncio.Lock] = [asyncio.Lock() for _ in range(TIME_WHEEL_SIZE)]
    all_connections: dict[WebSocket, WebSocketRoomState] = {}
    time_wheel: list[set[WebSocket]] = [set() for _ in range(TIME_WHEEL_SIZE)]
    time_wheel_index = 0

    @classmethod
    def register(cls, func: WS_VIEW):
        async def decorator(websocket: WebSocket):
            # Set timeout to slot 10 seconds later during initialization
            initial_index = (cls.time_wheel_index + 60) % TIME_WHEEL_SIZE
            cls.all_connections[websocket] = WebSocketRoomState(time_index=initial_index, sub_ids=[])
            async with cls.time_wheel_locks[initial_index]:
                cls.time_wheel[initial_index].add(websocket)
            await websocket.accept()
            context = context_from_websocket(websocket)
            checker = checker_from_websocket(websocket)
            try:
                # Receive and validate data
                data = await cls.receive_and_validate_data(websocket, cls.all_connections)
                if data is None:
                    return
                if data.type != 'init':
                    await websocket.send_text("Expected 'init' message type")
                    await websocket.close()
                    return

                # Get JWT from init message to generate a UUID for guest for heartbeat detection and message push conflict
                authorization = websocket.headers.get("authorization")
                logger.info(f"authorization: {authorization}")
                if not authorization or not authorization.startswith("Bearer "):
                    logger.warning("Not provided in 'init' message, logging in as guest.")
                    user_id = f"guest_{uuid7()}"
                else:
                    headers = {'Authorization': authorization}
                    result = checker.authorize(headers)
                    if result.verified:
                        if "sub" in result.data:
                            user_id = str(result.data["sub"])
                        else:
                            logger.error("'sub' key not found in JWT payload")
                            await websocket.send_text("'sub' key not found in JWT payload")
                            await websocket.close()
                            return
                    else:
                        logger.warning(f"JWT verification failed: {result.certificated}, logging in as guest.")
                        user_id = f"guest_{uuid7()}"
                if user_id.startswith("guest_"):
                    welcome_message = {
                        "message": "Welcome! You are logged in as a guest.",
                        "type": "welcome"
                    }
                else:
                    welcome_message = {
                        "message": "Welcome! Your authentication is successful.",
                        "type": "welcome"
                    }

                # await websocket.send_text(json.dumps(welcome_message))
                await websocket.send_json(welcome_message)
                subscriptions_group = data.data.get("subscriptions")
                await cls.subscribe(websocket, context, user_id, subscriptions_group)
                cls.all_connections[websocket].user_id = user_id

                await websocket.send_text("Start receiving subscription")

                # Read data in websocket
                while True:
                    try:
                        data = await cls.receive_and_validate_data(websocket, cls.all_connections)
                        if data is None:
                            break
                        match data.type:
                            case 'ping' | 'heartbeat':
                                await cls.reset_heartbeat(websocket)
                                await websocket.send_json({'type': 'pong'})
                            case 'follow_agent':
                                # Handle follow AI Agent
                                await cls.handle_follow_agent(websocket, data)
                            case 'unfollow_agent':
                                # Handle unfollow AI Agent
                                await cls.handle_unfollow_agent(websocket, data)
                            case _:
                                # Specific message processing function
                                await func(websocket, data)
                    except WebSocketDisconnect:
                        break

            except WebSocketDisconnect:
                pass

            except Exception as e:
                logger.error(f"Unexpected error in WebSocket connection: {e}", exc_info=True)

            finally:
                if websocket in cls.all_connections:
                    index = cls.all_connections[websocket].time_index
                    async with cls.time_wheel_locks[index]:
                        if websocket in cls.time_wheel[index]:
                            cls.time_wheel[index].remove(websocket)
                    for sub_id in cls.all_connections[websocket].sub_ids:
                        global_subscription.remove_subweb(sub_id, websocket)
                    del cls.all_connections[websocket]

        return decorator

    @classmethod
    async def receive_and_validate_data(cls, websocket: WebSocket, all_connections):
        """
        Receive and validate WebSocket data
        :param websocket: WebSocket connection object
        :return: Validated data object, returns None if validation fails
        """
        try:
            data = WebSocketRequest.model_validate(await websocket.receive_json())
            print(f"validated data: {data}")
            return data
        except WebSocketDisconnect as e:
            user_id = 'unknown'
            if websocket in all_connections:
                user_id = getattr(all_connections[websocket], 'user_id', 'unknown')
            logger.warning(f"WebSocket disconnected, user_id: {user_id}")
            raise
        except json.JSONDecodeError:
            logger.error("Received data is not a valid JSON: %s", await websocket.receive_text())
            await websocket.close(1001, 'Invalid JSON')
            return None
        except ValidationError as e:
            logger.error("Received data does not match the expected schema: %s")
            await websocket.close(1001, 'Invalid data format')
            return None

    # Tag binding
    @classmethod
    async def subscribe(cls, websocket: WebSocket, context: Context, user_id: str, subscriptions_group: str, no_tags: str = ""):
        """
        :param data: The received data object
        :return: User ID, returns None if authentication fails
        """
        try:
            # async with context.database.dogex() as session: source code
            async with context.database.dogex() as session:
                # User logs in and enters the group to listen to, otherwise defaults to the default subscription set
                if subscriptions_group != "" and subscriptions_group != None:
                    # Split the user subscription set from here, currently using '#' as separator
                    subscriptions_group_list = subscriptions_group.split("#")
                    # print("Subscription set list", subscriptions_group_list)
                    cls.all_connections[websocket].sub_ids = subscriptions_group_list
                    for sub_id in subscriptions_group_list:  # sub_id, subscription set id
                        if sub_id not in global_subscription.subweb.keys():
                            result = await session.execute(select(models.SubSet.tags)
                                                           .where(models.SubSet.id == uuid.UUID(sub_id)))
                            tag_list = result.scalars().first()
                            if not tag_list:
                                raise ValueError("Subscription set does not exist")
                            if tag_list:
                                # Need to lock when modifying shared structure
                                async with groups_lock:
                                    for t in tag_list:
                                        # Change to format: word: sub_id for easy calling
                                        key = f"{t}"
                                        # Use set to add sub_id
                                        global_subscription.sub.setdefault(key, set()).add(sub_id)
                                    global_subscription.add_subweb(sub_id, websocket)
                                # print(global_subscription.sub)
                        else:
                            # When subscription set already exists, binding WebSocket also requires locking
                            async with groups_lock:
                                global_subscription.add_subweb(sub_id, websocket)


                else:  # Here handle the default subscription set
                    return json.dumps({'code': 0, 'message': 'No subscription set uploaded', })
        except Exception as e:
            logger.error(f"Error processing subscriptions: {e}", exc_info=True)
            await websocket.send_text(f"Error processing subscriptions: {e}")
            await websocket.close()  # Disconnect here instead of returning None, otherwise subsequent sends will error
            return None
        return user_id

    @classmethod
    async def reset_heartbeat(cls, websocket: WebSocket):
        if websocket not in cls.all_connections:
            return

        # New slot = current time wheel pointer + 120
        current_index = cls.time_wheel_index
        new_index = (current_index + 120) % TIME_WHEEL_SIZE
        old_index = cls.all_connections[websocket].time_index

        # Lock in slot order to prevent deadlock
        lock_order = sorted([old_index, new_index])
        try:
            async with cls.time_wheel_locks[lock_order[0]]:
                async with cls.time_wheel_locks[lock_order[1]]:
                    # Remove from old slot
                    if websocket in cls.time_wheel[old_index]:
                        cls.time_wheel[old_index].remove(websocket)
                    # Add to new slot
                    cls.time_wheel[new_index].add(websocket)
                    # Update connection index
                    cls.all_connections[websocket].time_index = new_index
        except Exception as e:
            logger.error(f"Heartbeat reset failed: {e}")

    @classmethod
    async def next_heartbeat(cls):
        current_index = cls.time_wheel_index

        async with cls.time_wheel_locks[current_index]:
            current_connections = list(cls.time_wheel[current_index])
            if current_connections:
                cls.time_wheel[current_index].clear()

        # Close timeout connections
        for ws in current_connections:
            if ws in cls.all_connections:
                # global_subscription.remove_tags_user(cls.all_connections[ws].user_id)
                for sub_id in cls.all_connections[ws].sub_ids:
                    global_subscription.remove_subweb(sub_id, ws)
                del cls.all_connections[ws]
            try:
                await ws.close(1001, 'Heartbeat timeout')
                logger.debug("Client not responding")  # Change log level to DEBUG
            except Exception as e:
                logger.error(f"Close connection exception: {e}")

        # Move pointer
        cls.time_wheel_index = (current_index + 1) % TIME_WHEEL_SIZE


    @on_startup
    async def web_socket_heartbeat(app: FastAPI):
        if not isinstance(app, FastAPI):
            return

        async def heartbeat_loop():
            while True:
                try:
                    await WebSocketRoom.next_heartbeat()
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}", exc_info=True)
                    await asyncio.sleep(1)

        asyncio.create_task(heartbeat_loop())


@ws.websocket("/intelligence/")
@WebSocketRoom.register
async def subscription_websocket(websocket: WebSocket, data: WebSocketRequest):
    """
    Handle subscription WebSocket messages
    :param websocket: WebSocket connection object
    :param data: Received data object
    """
    pass


@on_startup
async def websocket_send_message(app: FastAPI):
    """Filter users and send messages"""
    if not isinstance(app, FastAPI):
        return

    context: Context = app.state.context
    await context.amqp.ensure_connection()
    await context.amqp._channel.declare_queue(name=settings.INTELLIGENCE_QUEUE, durable=True)

    async for message_data, message in context.amqp.receive(settings.INTELLIGENCE_QUEUE):
        try:
            if message.channel.is_closed:
                logger.warning("Message channel closed, reconnecting...")
                await context.amqp.ensure_connection()
                continue

            intelligence = json.loads(message.body.decode())

            if not intelligence.get("is_valuable"):
                logger.info(f"Filtered non-valuable intelligence: {intelligence.get('id')}")
                continue

            agent_tag = intelligence.get("agent_tag")
            logger.info(f"Processing intelligence {intelligence.get('id')} with agent_tag: {agent_tag}")

            # Enrich intelligence data
            intelligence = services.remove_part_info(intelligence)

            author_task = services.get_author_info(intelligence, context)
            monitor_task = services.get_monitor_time(intelligence["spider_time"], intelligence["published_at"])
            chain_task = services.get_all_chain_info(intelligence, context)

            intelligence["author"], intelligence["monitor_time"], chain_mapping_info = await asyncio.gather(
                author_task, monitor_task, chain_task
            )

            # Get AI agent info
            if agent_tag:
                ai_agents = await user_services.ai_agent_follow_services.get_ai_agent_list(app.state)
                agent = next((a for a in ai_agents if a.tag.slug == agent_tag), None)
                if agent:
                    intelligence["ai_agent"] = {"avatar": agent.avatar, "name": agent.name}

            intelligence["entities"] = services.handle_entity_info(intelligence["entities"], chain_mapping_info)

            # Send to subscribers
            await global_subscription.send_message(intelligence, {agent_tag} if agent_tag else set())

        except Exception as e:
            logger.exception(f"Error processing queue message: {e}")
        finally:
            await message.ack()

