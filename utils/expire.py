"""Disable expired services on remote panels."""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from database.db import async_session
from database.models import Service, Panel
from panels.factory import disable_user_on_panel

logger = logging.getLogger(__name__)


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
        for svc in services:
            try:
                panel = await session.get(Panel, svc.panel_id) if svc.panel_id else None
                if panel:
                    try:
                        await disable_user_on_panel(
                            panel_type=panel.panel_type,
                            base_url=panel.base_url,
                            username=svc.username,
                            panel_username=panel.username,
                            panel_password=panel.password,
                            token=panel.api_token,
                        )
                    except Exception as e:
                        logger.warning("Panel disable failed %s: %s", svc.username, e)
                svc.is_active = False
                logger.info("Expired service disabled: %s", svc.username)
            except Exception as e:
                logger.error("Expire process error %s: %s", svc.id, e)
        await session.commit()


async def expire_loop(interval_seconds: int = 300):
    while True:
        try:
            await process_expired_services()
        except Exception as e:
            logger.error("Expire loop: %s", e)
        await asyncio.sleep(interval_seconds)
