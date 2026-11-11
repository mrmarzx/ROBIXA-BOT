from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func
from config import settings
from database.models import Base, BotUser, Panel, Product, Setting, Card
import os

os.makedirs("data", exist_ok=True)
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    defaults = {
        "card_enabled": "0", "card_min": "10000", "card_max": "50000000",
        "card_random": "1", "card_security": "1",
        "zarinpal_enabled": "0", "zarinpal_merchant": "", "zarinpal_sandbox": "1",
        "aghay_enabled": "0", "stars_enabled": "0",
        "backup_interval_hours": "24",
        "support_username": settings.SUPPORT_USERNAME,
        "welcome_text": "", "support_text": "",
    }
    async with async_session() as session:
        for k, v in defaults.items():
            exists = await session.execute(select(Setting).where(Setting.key == k))
            if not exists.scalar_one_or_none():
                session.add(Setting(key=k, value=v))
        await session.commit()


async def get_or_create_user(telegram_id: int, username: str | None = None, full_name: str | None = None) -> BotUser:
    async with async_session() as session:
        result = await session.execute(select(BotUser).where(BotUser.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                changed = True
            if telegram_id in settings.admin_ids and not user.is_admin:
                user.is_admin = True
                changed = True
            if changed:
                await session.commit()
            return user
        user = BotUser(
            telegram_id=telegram_id, username=username, full_name=full_name,
            is_admin=telegram_id in settings.admin_ids, balance=0,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_user_by_telegram_id(telegram_id: int) -> BotUser | None:
    async with async_session() as session:
        result = await session.execute(select(BotUser).where(BotUser.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def get_user_by_id_or_username(query: str) -> BotUser | None:
    async with async_session() as session:
        if query.isdigit():
            tid = int(query)
            result = await session.execute(select(BotUser).where(BotUser.telegram_id == tid))
            user = result.scalar_one_or_none()
            if user:
                return user
            result = await session.execute(select(BotUser).where(BotUser.id == tid))
            return result.scalar_one_or_none()
        uname = query.lstrip("@").lower()
        result = await session.execute(select(BotUser).where(func.lower(BotUser.username) == uname))
        return result.scalar_one_or_none()


async def get_setting(key: str, default: str = "") -> str:
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        row = result.scalar_one_or_none()
        return row.value if row else default


async def set_setting(key: str, value: str):
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        row = result.scalar_one_or_none()
        if row:
            row.value = value
        else:
            session.add(Setting(key=key, value=value))
        await session.commit()


async def get_active_panels() -> list[Panel]:
    async with async_session() as session:
        result = await session.execute(select(Panel).where(Panel.is_active == True).order_by(Panel.id))
        return list(result.scalars().all())


async def get_panel(panel_id: int) -> Panel | None:
    async with async_session() as session:
        result = await session.execute(select(Panel).where(Panel.id == panel_id))
        return result.scalar_one_or_none()


async def get_active_products(panel_id: int | None = None) -> list[Product]:
    async with async_session() as session:
        query = select(Product).where(Product.is_active == True)
        if panel_id:
            query = query.where(Product.panel_id == panel_id)
        query = query.order_by(Product.sort_order, Product.id)
        result = await session.execute(query)
        return list(result.scalars().all())


async def get_product(product_id: int) -> Product | None:
    async with async_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()


async def get_active_cards() -> list[Card]:
    async with async_session() as session:
        result = await session.execute(select(Card).where(Card.is_active == True).order_by(Card.id))
        return list(result.scalars().all())


async def get_all_cards() -> list[Card]:
    async with async_session() as session:
        result = await session.execute(select(Card).order_by(Card.id))
        return list(result.scalars().all())
