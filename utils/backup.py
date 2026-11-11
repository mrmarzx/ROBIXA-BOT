"""
Automatic and manual backup / restore for ROBIXA BOT.
Creates a zip of data/ + .env and can restore from uploaded zip.
"""
from __future__ import annotations
import asyncio
import logging
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from config import settings

logger = logging.getLogger(__name__)

ROOT = Path(".").resolve()
DATA_DIR = ROOT / "data"
ENV_FILE = ROOT / ".env"
BACKUP_DIR = DATA_DIR / "backups"


def _ensure_dirs():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def create_backup_zip() -> Path:
    """Create a timestamped zip containing data/ and .env. Returns path."""
    _ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_path = BACKUP_DIR / f"robixa_backup_{ts}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # .env
        if ENV_FILE.is_file():
            zf.write(ENV_FILE, ".env")
        # data/ contents except previous backups to keep size reasonable
        if DATA_DIR.is_dir():
            for root, dirs, files in os.walk(DATA_DIR):
                # skip nested backups folder inside the walk for older zips
                if "backups" in Path(root).parts and Path(root) != BACKUP_DIR:
                    continue
                for name in files:
                    fp = Path(root) / name
                    # do not include the zip we are currently writing
                    if fp.resolve() == zip_path.resolve():
                        continue
                    # skip very large log files optionally
                    if fp.suffix == ".log" and fp.stat().st_size > 20 * 1024 * 1024:
                        continue
                    arcname = fp.relative_to(ROOT)
                    zf.write(fp, str(arcname))

    logger.info("Backup created: %s", zip_path)
    return zip_path


def restore_from_zip(zip_path: Path) -> None:
    """Extract backup zip into project root (overwrites data/ and .env)."""
    if not zip_path.is_file():
        raise FileNotFoundError(str(zip_path))
    with zipfile.ZipFile(zip_path, "r") as zf:
        # safety: only allow known paths
        for info in zf.infolist():
            name = info.filename
            if name.startswith("/") or ".." in name:
                raise ValueError(f"Unsafe path in zip: {name}")
            if not (name == ".env" or name.startswith("data/")):
                continue
            zf.extract(info, ROOT)
    logger.info("Restored from %s", zip_path)


async def send_backup_to_admins(bot: Bot, chat_ids: list[int] | None = None) -> Path | None:
    """Create backup and send document to given chat ids (admins)."""
    try:
        path = await asyncio.to_thread(create_backup_zip)
    except Exception as e:
        logger.error("Backup create failed: %s", e)
        return None

    targets = chat_ids or settings.admin_ids
    if not targets:
        # try BACKUP_CHAT_ID
        if settings.BACKUP_CHAT_ID and settings.BACKUP_CHAT_ID.lstrip("-").isdigit():
            targets = [int(settings.BACKUP_CHAT_ID)]
    if not targets:
        logger.warning("No admin chat to send backup")
        return path

    caption = (
        f"💾 بکاپ خودکار ROBIXA BOT\n"
        f"زمان: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"فایل: <code>{path.name}</code>"
    )
    for cid in targets:
        try:
            await bot.send_document(
                cid,
                FSInputFile(path),
                caption=caption,
            )
        except Exception as e:
            logger.warning("Send backup to %s failed: %s", cid, e)
    return path


async def backup_loop(bot: Bot, interval_hours: int = 24):
    """Background task: periodic backup."""
    # first run after 2 minutes
    await asyncio.sleep(120)
    while True:
        try:
            hours = interval_hours
            try:
                from database.db import get_setting
                raw = await get_setting("backup_interval_hours", str(interval_hours))
                hours = max(1, int(raw))
            except Exception:
                pass
            await send_backup_to_admins(bot)
        except Exception as e:
            logger.error("Backup loop error: %s", e)
        await asyncio.sleep(max(1, hours) * 3600)
