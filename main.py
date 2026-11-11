import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database.db import init_db
from handlers import common, user, admin
from utils.expire import expire_loop
from utils.backup import backup_loop

LOG_DIR = Path("data")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "robixa.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("robixa")


async def main():
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is empty. Run bash install.sh first.")
        sys.exit(1)

    logger.info(f"Starting {settings.BOT_NAME} v{settings.BOT_VERSION}")
    await init_db()
    logger.info("Database ready.")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(common.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)

    await bot.delete_webhook(drop_pending_updates=True)

    asyncio.create_task(expire_loop(interval_seconds=300))
    asyncio.create_task(
        backup_loop(bot, interval_hours=getattr(settings, "BACKUP_INTERVAL_HOURS", 24) or 24)
    )

    logger.info("ROBIXA BOT is running (expire + backup loops active).")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ROBIXA BOT stopped.")
