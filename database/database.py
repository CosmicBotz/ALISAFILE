"""
CosmicBotz — async MongoDB singleton for AlisaFile Store Bot.

Usage everywhere in the codebase:
    await CosmicBotz.add_user(user_id)
    await CosmicBotz.get_del_timer()
    etc.

No instance needed — all methods are classmethods on the singleton.
Call CosmicBotz.init() once at startup (done in main.py).
"""
import motor.motor_asyncio
import logging
from config import DB_URI, DB_NAME

logger = logging.getLogger(__name__)


class CosmicBotz:
    # ── Internal singleton state ───────────────────────────────────────────────
    _client             = None
    _db                 = None
    _users              = None
    _admins             = None
    _banned             = None
    _del_timer          = None
    _fsub               = None
    _req_fsub_channels  = None
    _caption            = None

    # ── Initialise once at startup ─────────────────────────────────────────────
    @classmethod
    def init(cls, uri: str = DB_URI, db_name: str = DB_NAME):
        """Call once in main.py before starting the bot."""
        cls._client            = motor.motor_asyncio.AsyncIOMotorClient(uri)
        cls._db                = cls._client[db_name]
        cls._users             = cls._db["users"]
        cls._admins            = cls._db["admins"]
        cls._banned            = cls._db["banned_user"]
        cls._del_timer         = cls._db["del_timer"]
        cls._fsub              = cls._db["fsub"]
        cls._req_fsub_channels = cls._db["request_forcesub_channel"]
        cls._caption           = cls._db["caption_settings"]
        logger.info(f"[CosmicBotz] Connected → {db_name}")

    # ── Users ──────────────────────────────────────────────────────────────────
    @classmethod
    async def present_user(cls, user_id: int) -> bool:
        return bool(await cls._users.find_one({"_id": user_id}))

    @classmethod
    async def add_user(cls, user_id: int):
        if not await cls.present_user(user_id):
            await cls._users.insert_one({"_id": user_id})

    @classmethod
    async def full_userbase(cls) -> list:
        docs = await cls._users.find().to_list(length=None)
        return [d["_id"] for d in docs]

    @classmethod
    async def del_user(cls, user_id: int):
        await cls._users.delete_one({"_id": user_id})

    # ── Admins ─────────────────────────────────────────────────────────────────
    @classmethod
    async def admin_exist(cls, admin_id: int) -> bool:
        return bool(await cls._admins.find_one({"_id": admin_id}))

    @classmethod
    async def add_admin(cls, admin_id: int):
        if not await cls.admin_exist(admin_id):
            await cls._admins.insert_one({"_id": admin_id})

    @classmethod
    async def del_admin(cls, admin_id: int):
        if await cls.admin_exist(admin_id):
            await cls._admins.delete_one({"_id": admin_id})

    @classmethod
    async def get_all_admins(cls) -> list:
        docs = await cls._admins.find().to_list(length=None)
        return [d["_id"] for d in docs]

    # ── Banned users ───────────────────────────────────────────────────────────
    @classmethod
    async def ban_user_exist(cls, user_id: int) -> bool:
        return bool(await cls._banned.find_one({"_id": user_id}))

    @classmethod
    async def add_ban_user(cls, user_id: int):
        if not await cls.ban_user_exist(user_id):
            await cls._banned.insert_one({"_id": user_id})

    @classmethod
    async def del_ban_user(cls, user_id: int):
        if await cls.ban_user_exist(user_id):
            await cls._banned.delete_one({"_id": user_id})

    @classmethod
    async def get_ban_users(cls) -> list:
        docs = await cls._banned.find().to_list(length=None)
        return [d["_id"] for d in docs]

    # ── Auto-delete timer ──────────────────────────────────────────────────────
    @classmethod
    async def set_del_timer(cls, value: int):
        existing = await cls._del_timer.find_one({})
        if existing:
            await cls._del_timer.update_one({}, {"$set": {"value": value}})
        else:
            await cls._del_timer.insert_one({"value": value})

    @classmethod
    async def get_del_timer(cls) -> int:
        data = await cls._del_timer.find_one({})
        return data.get("value", 0) if data else 0

    # ── Force-sub channels ─────────────────────────────────────────────────────
    @classmethod
    async def channel_exist(cls, channel_id: int) -> bool:
        return bool(await cls._fsub.find_one({"_id": channel_id}))

    @classmethod
    async def add_channel(cls, channel_id: int):
        if not await cls.channel_exist(channel_id):
            await cls._fsub.insert_one({"_id": channel_id, "mode": "on"})

    @classmethod
    async def rem_channel(cls, channel_id: int):
        if await cls.channel_exist(channel_id):
            await cls._fsub.delete_one({"_id": channel_id})

    @classmethod
    async def show_channels(cls) -> list:
        docs = await cls._fsub.find().to_list(length=None)
        return [d["_id"] for d in docs]

    @classmethod
    async def get_channel_mode(cls, channel_id: int) -> str:
        data = await cls._fsub.find_one({"_id": channel_id})
        return data.get("mode", "off") if data else "off"

    @classmethod
    async def set_channel_mode(cls, channel_id: int, mode: str):
        await cls._fsub.update_one(
            {"_id": channel_id}, {"$set": {"mode": mode}}, upsert=True
        )

    # ── Request FSub user tracking ─────────────────────────────────────────────
    @classmethod
    async def req_user(cls, channel_id: int, user_id: int):
        try:
            await cls._req_fsub_channels.update_one(
                {"_id": int(channel_id)},
                {"$addToSet": {"user_ids": int(user_id)}},
                upsert=True,
            )
        except Exception as e:
            logger.error(f"[CosmicBotz] req_user: {e}")

    @classmethod
    async def del_req_user(cls, channel_id: int, user_id: int):
        await cls._req_fsub_channels.update_one(
            {"_id": channel_id}, {"$pull": {"user_ids": user_id}}
        )

    @classmethod
    async def req_user_exist(cls, channel_id: int, user_id: int) -> bool:
        try:
            return bool(await cls._req_fsub_channels.find_one(
                {"_id": int(channel_id), "user_ids": int(user_id)}
            ))
        except Exception as e:
            logger.error(f"[CosmicBotz] req_user_exist: {e}")
            return False

    @classmethod
    async def reqChannel_exist(cls, channel_id: int) -> bool:
        return channel_id in await cls.show_channels()

    @classmethod
    def req_fsub_col(cls):
        """Direct collection access for advanced queries (e.g. /delreq)."""
        return cls._req_fsub_channels

    # ── Caption settings ───────────────────────────────────────────────────────
    @classmethod
    async def set_caption(cls, template: str):
        existing = await cls._caption.find_one({})
        if existing:
            await cls._caption.update_one({}, {"$set": {"template": template}})
        else:
            await cls._caption.insert_one({"template": template})

    @classmethod
    async def get_caption(cls):
        data = await cls._caption.find_one({})
        return data.get("template") if data else None
