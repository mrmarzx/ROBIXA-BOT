from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


class PanelType(str, enum.Enum):
    REBECCA = "REBECCA"
    MARZBAN = "MARZBAN"
    PASARGUARD = "PASARGUARD"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PaymentMethod(str, enum.Enum):
    CARD = "card"
    ZARINPAL = "zarinpal"
    AGHAY_PARDAKHT = "aghay_pardakht"
    STARS = "stars"


class BotUser(Base):
    __tablename__ = "bot_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE.value)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    services: Mapped[list["Service"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Panel(Base):
    __tablename__ = "panels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    panel_type: Mapped[str] = mapped_column(String(32), default=PanelType.REBECCA.value)
    base_url: Mapped[str] = mapped_column(String(512))
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    api_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    test_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    test_data_limit_gb: Mapped[int] = mapped_column(Integer, default=1)
    test_days: Mapped[int] = mapped_column(Integer, default=1)
    test_limit_days: Mapped[int] = mapped_column(Integer, default=42)
    extra_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    products: Mapped[list["Product"]] = relationship(back_populates="panel", cascade="all, delete-orphan")
    services: Mapped[list["Service"]] = relationship(back_populates="panel")


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("panels.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(BigInteger)
    data_limit_gb: Mapped[int] = mapped_column(Integer, default=0)
    days: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    panel: Mapped["Panel"] = relationship(back_populates="products")
    services: Mapped[list["Service"]] = relationship(back_populates="product")


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"))
    panel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("panels.id", ondelete="SET NULL"), nullable=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    username: Mapped[str] = mapped_column(String(64), index=True)
    password: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    data_limit_gb: Mapped[int] = mapped_column(Integer, default=0)
    expire_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner: Mapped["BotUser"] = relationship(back_populates="services")
    panel: Mapped[Optional["Panel"]] = relationship(back_populates="services")
    product: Mapped[Optional["Product"]] = relationship(back_populates="services")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"))
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING.value)
    payment_method: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tracking_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    receipt_file_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    security_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped["BotUser"] = relationship(back_populates="orders")


class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_number: Mapped[str] = mapped_column(String(32))
    card_holder: Mapped[str] = mapped_column(String(128))
    bank_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
