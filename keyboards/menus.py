from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from texts import fa as t


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=t.BTN_BUY), KeyboardButton(text=t.BTN_TEST))
    builder.row(KeyboardButton(text=t.BTN_MY_SERVICES), KeyboardButton(text=t.BTN_WALLET))
    builder.row(KeyboardButton(text=t.BTN_SUPPORT))
    if is_admin:
        builder.row(KeyboardButton(text=t.BTN_ADMIN))
    return builder.as_markup(resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=t.BTN_PANELS), KeyboardButton(text=t.BTN_PRODUCTS))
    builder.row(KeyboardButton(text=t.BTN_USERS), KeyboardButton(text=t.BTN_BANKING))
    builder.row(KeyboardButton(text=t.BTN_BROADCAST), KeyboardButton(text=t.BTN_TEXTS))
    builder.row(KeyboardButton(text=t.BTN_BACKUP), KeyboardButton(text=t.BTN_BACK))
    return builder.as_markup(resize_keyboard=True)


def panels_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text=t.ADD_PANEL, callback_data="panel:add"),
        InlineKeyboardButton(text=t.LIST_PANELS, callback_data="panel:list"),
    )
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="admin:back"))
    return b.as_markup()


def panel_type_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🟢 REBECCA", callback_data="panel_type:REBECCA"))
    b.row(InlineKeyboardButton(text="🔵 MARZBAN", callback_data="panel_type:MARZBAN"))
    b.row(InlineKeyboardButton(text="🟣 PASARGUARD", callback_data="panel_type:PASARGUARD"))
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="panel:menu"))
    return b.as_markup()


def products_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text=t.ADD_PRODUCT, callback_data="product:add"),
        InlineKeyboardButton(text="📋 لیست محصولات", callback_data="product:list"),
    )
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="admin:back"))
    return b.as_markup()


def product_list_keyboard(products: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in products:
        b.row(InlineKeyboardButton(
            text=f"{p.name} — {p.price:,} تومان",
            callback_data=f"buy:{p.id}",
        ))
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="user:main"))
    return b.as_markup()


def confirm_buy_keyboard(product_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ تأیید خرید", callback_data=f"confirm_buy:{product_id}"),
        InlineKeyboardButton(text="❌ انصراف", callback_data="user:main"),
    )
    return b.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="❌ لغو", callback_data="cancel"))
    return b.as_markup()


def support_keyboard(support_username: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    uname = support_username.lstrip("@")
    b.row(InlineKeyboardButton(text="💬 پیام به پشتیبانی", url=f"https://t.me/{uname}"))
    return b.as_markup()


def wallet_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=t.BTN_CHARGE, callback_data="wallet:charge"))
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="user:main"))
    return b.as_markup()


def charge_methods_keyboard(card_on: bool, zarin_on: bool, stars_on: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if card_on:
        b.row(InlineKeyboardButton(text="💳 کارت به کارت (دستی)", callback_data="pay:card"))
    if zarin_on:
        b.row(InlineKeyboardButton(text="🟢 زرین‌پال (اتوماتیک)", callback_data="pay:zarinpal"))
    if stars_on:
        b.row(InlineKeyboardButton(text="⭐ استارز تلگرام", callback_data="pay:stars"))
    if not (card_on or zarin_on or stars_on):
        b.row(InlineKeyboardButton(text="⚠️ هیچ روشی فعال نیست", callback_data="noop"))
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="wallet:back"))
    return b.as_markup()


def banking_menu(card_on: bool, zarin_on: bool, aghay_on: bool, stars_on: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    card_status = "🟢" if card_on else "🔴"
    zarin_status = "🟢" if zarin_on else "🔴"
    aghay_status = "🟢" if aghay_on else "🔴"
    stars_status = "🟢" if stars_on else "🔴"
    b.row(InlineKeyboardButton(text=f"{card_status} شماره کارت | دستی", callback_data="bank:card"))
    b.row(InlineKeyboardButton(text=f"{zarin_status} زرین‌پال | اتوماتیک", callback_data="bank:zarinpal"))
    b.row(InlineKeyboardButton(text=f"{aghay_status} آقای پرداخت | اتوماتیک", callback_data="bank:aghay"))
    b.row(InlineKeyboardButton(text=f"{stars_status} استارز تلگرام | اتوماتیک", callback_data="bank:stars"))
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="admin:back"))
    return b.as_markup()


def card_settings_menu(enabled: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    status = t.TOGGLE_ON if enabled else t.TOGGLE_OFF
    b.row(InlineKeyboardButton(text=f"وضعیت نمایش: {status}", callback_data="card:toggle"))
    b.row(InlineKeyboardButton(text="⚙️ تنظیمات پرداخت", callback_data="card:settings"))
    b.row(InlineKeyboardButton(text="📋 مدیریت شماره کارت‌ها", callback_data="card:list"))
    b.row(InlineKeyboardButton(text="➕ افزودن کارت", callback_data="card:add"))
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="bank:menu"))
    return b.as_markup()


def user_manage_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💰 شارژ پول", callback_data=f"u:charge:{telegram_id}"),
        InlineKeyboardButton(text="🗑 صفر کردن موجودی", callback_data=f"u:zero:{telegram_id}"),
    )
    b.row(InlineKeyboardButton(text="✉️ پیام به کاربر", callback_data=f"u:msg:{telegram_id}"))
    b.row(
        InlineKeyboardButton(text="🚫 مسدود کردن", callback_data=f"u:block:{telegram_id}"),
        InlineKeyboardButton(text="✅ رفع مسدودی", callback_data=f"u:unblock:{telegram_id}"),
    )
    b.row(InlineKeyboardButton(text="📦 مشاهده سرویس‌ها", callback_data=f"u:services:{telegram_id}"))
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="admin:users"))
    return b.as_markup()


def approve_reject_keyboard(order_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ تأیید", callback_data=f"order:ok:{order_id}"),
        InlineKeyboardButton(text="❌ رد", callback_data=f"order:no:{order_id}"),
    )
    return b.as_markup()
