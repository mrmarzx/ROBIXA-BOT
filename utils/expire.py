"""Disable expired reseller admins and notify owners."""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from database.db import async_session
from database.models import Service, Panel, BotUser
from panels.factory import disable_reseller_on_panel
from texts import fa as t
from keyboards.menus import my_service_actions

logger = logging.getLogger(__name__)

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


async def process_expired_services():
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        result = await session.execute(
            select(Service).where(
                Service.is_active == True,
                Service.expire_at != None,
                Service.expire_at <= now,
            )
        )
        services = list(result.scalars().all())
        notify_list = []
        for svc in services:
            try:
                panel = await session.get(Panel, svc.panel_id) if svc.panel_id else None
                snapshot: list[str] = []
                if panel:
                    try:
                        snapshot = await disable_reseller_on_panel(
                            panel_type=panel.panel_type,
                            base_url=panel.base_url,
                            admin_username=svc.username,
                            panel_username=panel.username,
                            panel_password=panel.password,
                            token=panel.api_token,
                        )
                    except Exception as e:
                        logger.warning("Reseller disable failed %s: %s", svc.username, e)
                svc.is_active = False
                svc.disabled_users_snapshot = {"users": snapshot or []}
                owner = await session.get(BotUser, svc.owner_id)
                if owner:
                    notify_list.append((owner.telegram_id, svc.id, svc.username))
                logger.info(
                    "Expired reseller disabled: %s (users: %d)",
                    svc.username,
                    len(snapshot or []),
                )
            except Exception as e:
                logger.error("Expire process error %s: %s", svc.id, e)
        await session.commit()

    if _bot and notify_list:
        for tid, sid, uname in notify_list:
            try:
                await _bot.send_message(
                    tid,
                    t.EXPIRED_NOTIFY.format(username=uname),
                    reply_markup=my_service_actions(sid, is_active=False),
                )
            except Exception as e:
                logger.warning("notify expire %s: %s", tid, e)


async def expire_loop(interval_seconds: int = 300):
    while True:
        try:
            await process_expired_services()
        except Exception as e:
            logger.error("Expire loop: %s", e)
        await asyncio.sleep(interval_seconds)
