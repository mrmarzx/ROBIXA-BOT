from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from texts import fa as t


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=t.BTN_BUY), KeyboardButton(text=t.BTN_TEST))
    b.row(KeyboardButton(text=t.BTN_MY_SERVICES), KeyboardButton(text=t.BTN_WALLET))
    b.row(KeyboardButton(text=t.BTN_SUPPORT))
    if is_admin:
        b.row(KeyboardButton(text=t.BTN_ADMIN))
    return b.as_markup(resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=t.BTN_PANELS), KeyboardButton(text=t.BTN_PRODUCTS))
    b.row(KeyboardButton(text=t.BTN_USERS), KeyboardButton(text=t.BTN_BANKING))
    b.row(KeyboardButton(text=t.BTN_BROADCAST), KeyboardButton(text=t.BTN_STATS))
    b.row(KeyboardButton(text=t.BTN_BACKUP), KeyboardButton(text=t.BTN_TEXTS))
    b.row(KeyboardButton(text=t.BTN_BACK))
    return b.as_markup(resize_keyboard=True)


def wallet_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=t.BTN_CHARGE, callback_data="wallet:charge"))
    return b.as_markup()


def charge_methods_keyboard(card_on: bool, zarin_on: bool, stars_on: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if card_on:
        b.row(InlineKeyboardButton(text="💳 کارت به کارت", callback_data="pay:card"))
    if zarin_on:
        b.row(InlineKeyboardButton(text="🟣 زرین‌پال", callback_data="pay:zarinpal"))
    if stars_on:
        b.row(InlineKeyboardButton(text="⭐ تلگرام Stars", callback_data="pay:stars"))
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="wallet:back"))
    return b.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="❌ انصراف", callback_data="cancel"))
    return b.as_markup()


def product_list_keyboard(products) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in products:
        label = f"{p.name} — {p.price:,} ت"
        b.row(InlineKeyboardButton(text=label, callback_data=f"buy:{p.id}"))
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="cancel"))
    return b.as_markup()


def confirm_buy_keyboard(product_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ تأیید خرید", callback_data=f"buyok:{product_id}"),
        InlineKeyboardButton(text="❌ انصراف", callback_data="cancel"),
    )
    return b.as_markup()


def support_keyboard(username: str) -> InlineKeyboardMarkup:
    uname = (username or "Support").lstrip("@")
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="💬 پیام به پشتیبانی", url=f"https://t.me/{uname}"))
    return b.as_markup()


def panels_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➕ افزودن پنل", callback_data="panel:add"))
    b.row(InlineKeyboardButton(text="📋 لیست پنل‌ها", callback_data="panel:list"))
    return b.as_markup()


def panel_type_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="💜 REBECCA", callback_data="panel_type:REBECCA"))
    b.row(InlineKeyboardButton(text="🔵 MARZBAN", callback_data="panel_type:MARZBAN"))
    b.row(InlineKeyboardButton(text="🟢 PASARGUARD", callback_data="panel_type:PASARGUARD"))
    b.row(InlineKeyboardButton(text="🔙", callback_data="panel:menu"))
    return b.as_markup()


def products_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➕ افزودن محصول", callback_data="product:add"))
    b.row(InlineKeyboardButton(text="📋 لیست محصولات", callback_data="product:list"))
    return b.as_markup()


def banking_menu(card_on: bool, zarin_on: bool, aghay_on: bool = False, stars_on: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text=f"💳 کارت‌به‌کارت {'✅' if card_on else '❌'}",
        callback_data="bank:card",
    ))
    b.row(InlineKeyboardButton(
        text=f"🟣 زرین‌پال {'✅' if zarin_on else '❌'}",
        callback_data="bank:zarinpal",
    ))
    b.row(InlineKeyboardButton(text="➕ افزودن کارت", callback_data="bank:addcard"))
    b.row(InlineKeyboardButton(text="📋 کارت‌ها", callback_data="bank:cards"))
    return b.as_markup()


def card_settings_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔙 بانکی", callback_data="bank:menu"))
    return b.as_markup()


def approve_reject_keyboard(order_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ تأیید", callback_data=f"order:ok:{order_id}"),
        InlineKeyboardButton(text="❌ رد", callback_data=f"order:no:{order_id}"),
    )
    return b.as_markup()


def user_manage_keyboard(tid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💰 شارژ", callback_data=f"u:charge:{tid}"),
        InlineKeyboardButton(text="🗑 صفر", callback_data=f"u:zero:{tid}"),
    )
    b.row(
        InlineKeyboardButton(text="📩 پیام", callback_data=f"u:msg:{tid}"),
        InlineKeyboardButton(text="📦 نمایندگی‌ها", callback_data=f"u:services:{tid}"),
    )
    b.row(
        InlineKeyboardButton(text="🚫 بلاک", callback_data=f"u:block:{tid}"),
        InlineKeyboardButton(text="✅ آنبلاک", callback_data=f"u:unblock:{tid}"),
    )
    return b.as_markup()


def my_service_actions(service_id: int, is_active: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_active:
        b.row(InlineKeyboardButton(text="🔑 تغییر پسورد", callback_data=f"svc:pass:{service_id}"))
    else:
        b.row(InlineKeyboardButton(text="♻️ تمدید با کیف پول", callback_data=f"svc:renew:{service_id}"))
    return b.as_markup()


def renew_confirm_keyboard(service_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ تأیید تمدید", callback_data=f"svc:renewok:{service_id}"),
        InlineKeyboardButton(text="❌ انصراف", callback_data="cancel"),
    )
    return b.as_markup()
