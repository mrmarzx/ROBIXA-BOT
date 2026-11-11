import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from datetime import datetime, timezone

from config import settings
from database.db import (
    get_or_create_user, async_session, get_active_panels, get_panel,
    get_setting, set_setting, get_user_by_id_or_username, get_all_cards,
)
from database.models import Panel, Product, Card, Order, BotUser, Service, OrderStatus
from keyboards.menus import (
    panels_menu, panel_type_keyboard, products_menu, cancel_keyboard,
    admin_menu, banking_menu, card_settings_menu, user_manage_keyboard,
)
from texts import fa as t
from panels.factory import test_panel_connection

router = Router()


class AddPanelStates(StatesGroup):
    waiting_type = State()
    waiting_name = State()
    waiting_url = State()
    waiting_username = State()
    waiting_password = State()
    waiting_token = State()


class AddProductStates(StatesGroup):
    waiting_panel = State()
    waiting_name = State()
    waiting_price = State()
    waiting_data = State()
    waiting_days = State()


class AddCardStates(StatesGroup):
    waiting_number = State()
    waiting_holder = State()
    waiting_bank = State()


class UserManageStates(StatesGroup):
    waiting_query = State()
    waiting_charge_amount = State()
    waiting_message = State()


class CardSettingStates(StatesGroup):
    waiting_min = State()
    waiting_max = State()


def is_admin(user_id: int, db_is_admin: bool) -> bool:
    return db_is_admin or user_id in settings.admin_ids


# ==================== Panels ====================
@router.message(F.text == t.BTN_PANELS)
async def panels_handler(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    if not is_admin(message.from_user.id, user.is_admin):
        await message.answer(t.NOT_ADMIN)
        return
    await message.answer("🖥 مدیریت پنل‌ها", reply_markup=panels_menu())


@router.callback_query(F.data == "panel:menu")
async def panel_menu_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🖥 مدیریت پنل‌ها", reply_markup=panels_menu())
    await callback.answer()


@router.callback_query(F.data == "panel:add")
async def panel_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddPanelStates.waiting_type)
    await callback.message.edit_text(
        "نوع پنل را انتخاب کنید:\n\nدر فاز فعلی فقط <b>REBECCA</b> پشتیبانی می‌شود.",
        reply_markup=panel_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("panel_type:"))
async def panel_type_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(panel_type=callback.data.split(":")[1])
    await state.set_state(AddPanelStates.waiting_name)
    await callback.message.edit_text(
        "نام دلخواه پنل را وارد کنید:\n(مثلاً: سرور آلمان ۱)",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AddPanelStates.waiting_name)
async def panel_name_received(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddPanelStates.waiting_url)
    await message.answer(
        "آدرس پنل را وارد کنید:\nمثال: <code>https://panel.example.com:8000</code>\n⚠️ بدون اسلش انتهایی",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddPanelStates.waiting_url)
async def panel_url_received(message: Message, state: FSMContext):
    url = message.text.strip().rstrip("/")
    if not url.startswith("http"):
        await message.answer("❌ آدرس باید با http:// یا https:// شروع شود.")
        return
    await state.update_data(base_url=url)
    await state.set_state(AddPanelStates.waiting_username)
    await message.answer(
        "نام کاربری ادمین پنل:\n(اگر فقط توکن دارید <code>-</code> بفرستید)",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddPanelStates.waiting_username)
async def panel_username_received(message: Message, state: FSMContext):
    u = message.text.strip()
    await state.update_data(username=None if u == "-" else u)
    await state.set_state(AddPanelStates.waiting_password)
    await message.answer(
        "رمز عبور ادمین پنل:\n(اگر فقط توکن دارید <code>-</code> بفرستید)",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddPanelStates.waiting_password)
async def panel_password_received(message: Message, state: FSMContext):
    p = message.text.strip()
    await state.update_data(password=None if p == "-" else p)
    await state.set_state(AddPanelStates.waiting_token)
    await message.answer(
        "توکن / API Key پنل:\n"
        "• برای <b>REBECCA / MARZBAN</b>: JWT یا خالی با <code>-</code>\n"
        "• برای <b>PASARGUARD</b>: حتماً <code>X-Api-Key</code> را وارد کنید\n"
        "اگر ندارید <code>-</code> بفرستید.",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddPanelStates.waiting_token)
async def panel_token_received(message: Message, state: FSMContext):
    token = message.text.strip()
    if token == "-":
        token = None
    data = await state.get_data()
    await state.clear()

    await message.answer("⏳ در حال تست اتصال به پنل...")
    try:
        result = await test_panel_connection(
            panel_type=data["panel_type"],
            base_url=data["base_url"],
            username=data.get("username"),
            password=data.get("password"),
            token=token,
        )
        if not result.get("ok"):
            await message.answer(t.PANEL_CONNECTION_FAILED.format(error=result.get("error") or result.get("detail")))
            return
    except Exception as e:
        await message.answer(t.PANEL_CONNECTION_FAILED.format(error=str(e)))
        return

    async with async_session() as session:
        panel = Panel(
            name=data["name"],
            panel_type=data["panel_type"],
            base_url=data["base_url"],
            username=data.get("username"),
            password=data.get("password"),
            api_token=token,
            is_active=True,
            test_enabled=True,
            test_data_limit_gb=1,
            test_days=1,
            test_limit_days=42,
        )
        session.add(panel)
        await session.commit()
        await session.refresh(panel)

    await message.answer(
        t.PANEL_ADDED_SUCCESS + f"\n\n🆔 شناسه: <code>{panel.id}</code>\nنام: {panel.name}\nنوع: {panel.panel_type}",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "panel:list")
async def panel_list_cb(callback: CallbackQuery):
    panels = await get_active_panels()
    if not panels:
        await callback.message.edit_text("هیچ پنلی ثبت نشده.", reply_markup=panels_menu())
        await callback.answer()
        return
    lines = ["📋 <b>لیست پنل‌ها:</b>\n"]
    for p in panels:
        status = "🟢" if p.is_active else "🔴"
        test = "✅ تست فعال" if p.test_enabled else "⏸ تست خاموش"
        lines.append(
            f"{status} <b>{p.name}</b> (ID:{p.id})\n"
            f"   نوع: {p.panel_type} | {test}\n"
            f"   <code>{p.base_url}</code>\n"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=panels_menu())
    await callback.answer()


# ==================== Products ====================
@router.message(F.text == t.BTN_PRODUCTS)
async def products_handler(message: Message):
    user = await get_or_create_user(message.from_user.id)
    if not is_admin(message.from_user.id, user.is_admin):
        await message.answer(t.NOT_ADMIN)
        return
    await message.answer("📦 مدیریت محصولات", reply_markup=products_menu())


@router.callback_query(F.data == "product:add")
async def product_add_start(callback: CallbackQuery, state: FSMContext):
    panels = await get_active_panels()
    if not panels:
        await callback.answer("ابتدا یک پنل اضافه کنید.", show_alert=True)
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    for p in panels:
        b.row(InlineKeyboardButton(text=f"{p.name} ({p.panel_type})", callback_data=f"prod_panel:{p.id}"))
    b.row(InlineKeyboardButton(text=t.BTN_BACK, callback_data="admin:back"))
    await state.set_state(AddProductStates.waiting_panel)
    await callback.message.edit_text("پنل مربوط به محصول را انتخاب کنید:", reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("prod_panel:"))
async def product_panel_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(panel_id=int(callback.data.split(":")[1]))
    await state.set_state(AddProductStates.waiting_name)
    await callback.message.edit_text("نام محصول:\nمثال: ۳۰ روزه نامحدود", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AddProductStates.waiting_name)
async def product_name_received(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProductStates.waiting_price)
    await message.answer("قیمت به تومان:\nمثال: 450000", reply_markup=cancel_keyboard())


@router.message(AddProductStates.waiting_price)
async def product_price_received(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip().replace(",", ""))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ قیمت نامعتبر.")
        return
    await state.update_data(price=price)
    await state.set_state(AddProductStates.waiting_data)
    await message.answer("حجم گیگابایت (۰ = نامحدود):\nمثال: 50", reply_markup=cancel_keyboard())


@router.message(AddProductStates.waiting_data)
async def product_data_received(message: Message, state: FSMContext):
    try:
        data_gb = int(message.text.strip())
        if data_gb < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ عدد نامعتبر.")
        return
    await state.update_data(data_limit_gb=data_gb)
    await state.set_state(AddProductStates.waiting_days)
    await message.answer("مدت به روز:\nمثال: 30", reply_markup=cancel_keyboard())


@router.message(AddProductStates.waiting_days)
async def product_days_received(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ عدد نامعتبر.")
        return
    data = await state.get_data()
    await state.clear()
    async with async_session() as session:
        product = Product(
            panel_id=data["panel_id"],
            name=data["name"],
            price=data["price"],
            data_limit_gb=data["data_limit_gb"],
            days=days,
            is_active=True,
        )
        session.add(product)
        await session.commit()
    await message.answer(t.PRODUCT_CREATED.format(name=data["name"]), reply_markup=admin_menu())


@router.callback_query(F.data == "product:list")
async def product_list_cb(callback: CallbackQuery):
    from database.db import get_active_products
    products = await get_active_products()
    if not products:
        await callback.message.edit_text("هیچ محصولی تعریف نشده.", reply_markup=products_menu())
        await callback.answer()
        return
    lines = ["📋 <b>لیست محصولات:</b>\n"]
    for p in products:
        data = "∞" if p.data_limit_gb == 0 else f"{p.data_limit_gb}GB"
        lines.append(f"• <b>{p.name}</b>\n  💰 {p.price:,} | {data} | {p.days} روز\n")
    await callback.message.edit_text("\n".join(lines), reply_markup=products_menu())
    await callback.answer()


# ==================== Banking ====================
@router.message(F.text == t.BTN_BANKING)
async def banking_handler(message: Message):
    user = await get_or_create_user(message.from_user.id)
    if not is_admin(message.from_user.id, user.is_admin):
        await message.answer(t.NOT_ADMIN)
        return
    card_on = (await get_setting("card_enabled", "0")) == "1"
    zarin_on = (await get_setting("zarinpal_enabled", "0")) == "1"
    aghay_on = (await get_setting("aghay_enabled", "0")) == "1"
    stars_on = (await get_setting("stars_enabled", "0")) == "1"
    await message.answer(t.BANKING_MENU, reply_markup=banking_menu(card_on, zarin_on, aghay_on, stars_on))


@router.callback_query(F.data == "bank:menu")
async def bank_menu_cb(callback: CallbackQuery):
    card_on = (await get_setting("card_enabled", "0")) == "1"
    zarin_on = (await get_setting("zarinpal_enabled", "0")) == "1"
    aghay_on = (await get_setting("aghay_enabled", "0")) == "1"
    stars_on = (await get_setting("stars_enabled", "0")) == "1"
    await callback.message.edit_text(t.BANKING_MENU, reply_markup=banking_menu(card_on, zarin_on, aghay_on, stars_on))
    await callback.answer()


@router.callback_query(F.data == "bank:card")
async def bank_card_cb(callback: CallbackQuery):
    enabled = (await get_setting("card_enabled", "0")) == "1"
    await callback.message.edit_text("💳 مدیریت کارت به کارت", reply_markup=card_settings_menu(enabled))
    await callback.answer()


@router.callback_query(F.data == "card:toggle")
async def card_toggle(callback: CallbackQuery):
    current = await get_setting("card_enabled", "0")
    new = "0" if current == "1" else "1"
    await set_setting("card_enabled", new)
    enabled = new == "1"
    await callback.message.edit_text("💳 مدیریت کارت به کارت", reply_markup=card_settings_menu(enabled))
    await callback.answer("وضعیت تغییر کرد ✅")


@router.callback_query(F.data == "card:settings")
async def card_settings(callback: CallbackQuery, state: FSMContext):
    min_a = await get_setting("card_min", "10000")
    max_a = await get_setting("card_max", "50000000")
    rnd = await get_setting("card_random", "1")
    sec = await get_setting("card_security", "1")
    text = (
        f"⚙️ تنظیمات کارت به کارت\n\n"
        f"حداقل: {int(min_a):,}\nحداکثر: {int(max_a):,}\n"
        f"نمایش رندوم کارت: {'بله' if rnd=='1' else 'خیر'}\n"
        f"مبلغ امنیتی: {'فعال' if sec=='1' else 'غیرفعال'}\n\n"
        f"برای تغییر حداقل، عدد جدید را بفرستید یا /skip"
    )
    await state.set_state(CardSettingStates.waiting_min)
    await callback.message.edit_text(text, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(CardSettingStates.waiting_min)
async def card_min_set(message: Message, state: FSMContext):
    if message.text.strip() != "/skip":
        try:
            v = int(message.text.strip().replace(",", ""))
            await set_setting("card_min", str(v))
        except ValueError:
            await message.answer("❌ عدد نامعتبر")
            return
    await state.set_state(CardSettingStates.waiting_max)
    await message.answer("حداکثر مبلغ را وارد کنید یا /skip")


@router.message(CardSettingStates.waiting_max)
async def card_max_set(message: Message, state: FSMContext):
    if message.text.strip() != "/skip":
        try:
            v = int(message.text.strip().replace(",", ""))
            await set_setting("card_max", str(v))
        except ValueError:
            await message.answer("❌ عدد نامعتبر")
            return
    await state.clear()
    await message.answer("✅ تنظیمات ذخیره شد.", reply_markup=admin_menu())


@router.callback_query(F.data == "card:list")
async def card_list(callback: CallbackQuery):
    cards = await get_all_cards()
    if not cards:
        await callback.message.edit_text("هیچ کارتی ثبت نشده.", reply_markup=card_settings_menu(True))
        await callback.answer()
        return
    lines = ["📋 کارت‌ها:\n"]
    for c in cards:
        st = "🟢" if c.is_active else "🔴"
        lines.append(f"{st} <code>{c.card_number}</code>\n   {c.card_holder} | {c.bank_name or '-'}\n")
    await callback.message.edit_text("\n".join(lines), reply_markup=card_settings_menu(True))
    await callback.answer()


@router.callback_query(F.data == "card:add")
async def card_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCardStates.waiting_number)
    await callback.message.edit_text("شماره کارت را وارد کنید (۱۶ رقم):", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AddCardStates.waiting_number)
async def card_number(message: Message, state: FSMContext):
    num = message.text.strip().replace("-", "").replace(" ", "")
    if not num.isdigit() or len(num) < 12:
        await message.answer("❌ شماره کارت نامعتبر.")
        return
    await state.update_data(card_number=num)
    await state.set_state(AddCardStates.waiting_holder)
    await message.answer("نام صاحب کارت:", reply_markup=cancel_keyboard())


@router.message(AddCardStates.waiting_holder)
async def card_holder(message: Message, state: FSMContext):
    await state.update_data(card_holder=message.text.strip())
    await state.set_state(AddCardStates.waiting_bank)
    await message.answer("نام بانک (اختیاری، یا - ):", reply_markup=cancel_keyboard())


@router.message(AddCardStates.waiting_bank)
async def card_bank(message: Message, state: FSMContext):
    bank = message.text.strip()
    if bank == "-":
        bank = None
    data = await state.get_data()
    await state.clear()
    async with async_session() as session:
        card = Card(
            card_number=data["card_number"],
            card_holder=data["card_holder"],
            bank_name=bank,
            is_active=True,
        )
        session.add(card)
        await session.commit()
    await message.answer("✅ کارت اضافه شد.", reply_markup=admin_menu())


class ZarinpalStates(StatesGroup):
    waiting_merchant = State()


@router.callback_query(F.data == "bank:zarinpal")
async def bank_zarin(callback: CallbackQuery, state: FSMContext):
    enabled = (await get_setting("zarinpal_enabled", "0")) == "1"
    merchant = await get_setting("zarinpal_merchant", "")
    sandbox = await get_setting("zarinpal_sandbox", "1")
    text = (
        f"🟢 <b>زرین‌پال</b>\n\n"
        f"وضعیت: {'🟢 روشن' if enabled else '🔴 خاموش'}\n"
        f"مرچنت: <code>{merchant[:8] + '...' if len(merchant) > 8 else (merchant or '-')}</code>\n"
        f"سندباکس: {'بله' if sandbox == '1' else 'خیر'}\n\n"
        f"مرچنت‌آیدی ۳۶ کاراکتری را ارسال کنید یا برای تغییر وضعیت /toggle بفرستید."
    )
    await state.set_state(ZarinpalStates.waiting_merchant)
    await callback.message.edit_text(text, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(ZarinpalStates.waiting_merchant)
async def zarin_merchant_set(message: Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "/toggle":
        cur = await get_setting("zarinpal_enabled", "0")
        await set_setting("zarinpal_enabled", "0" if cur == "1" else "1")
        await state.clear()
        await message.answer("✅ وضعیت زرین‌پال تغییر کرد.", reply_markup=admin_menu())
        return
    if len(txt) < 20:
        await message.answer("❌ مرچنت‌آیدی معتبر نیست.")
        return
    await set_setting("zarinpal_merchant", txt)
    await set_setting("zarinpal_enabled", "1")
    # quick test
    from payments.zarinpal import Zarinpal
    sandbox = (await get_setting("zarinpal_sandbox", "1")) == "1"
    zp = Zarinpal(merchant_id=txt, sandbox=sandbox)
    result = await zp.test_merchant()
    await state.clear()
    if result.get("ok"):
        await message.answer("✅ مرچنت ذخیره و اتصال تست شد.", reply_markup=admin_menu())
    else:
        await message.answer(
            f"✅ مرچنت ذخیره شد.\n⚠️ تست اتصال: {result.get('error')}\n"
            f"(اگر سندباکس/مرچنت درست باشد بعداً کار می‌کند)",
            reply_markup=admin_menu(),
        )



@router.callback_query(F.data == "bank:aghay")
async def bank_aghay(callback: CallbackQuery):
    await callback.answer("آقای پرداخت در فاز بعدی.", show_alert=True)


@router.callback_query(F.data == "bank:stars")
async def bank_stars(callback: CallbackQuery):
    await callback.answer("استارز تلگرام در فاز بعدی.", show_alert=True)


# ==================== Order Approve / Reject ====================
@router.callback_query(F.data.startswith("order:ok:"))
async def order_approve(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.status != OrderStatus.PENDING.value:
            await callback.answer("سفارش معتبر نیست.", show_alert=True)
            return
        user = await session.get(BotUser, order.user_id)
        user.balance += order.amount
        order.status = OrderStatus.COMPLETED.value
        order.completed_at = datetime.now(timezone.utc)
        await session.commit()
        new_balance = user.balance
        tid = user.telegram_id

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ تأیید شد توسط ادمین",
    )
    await callback.answer("تأیید شد")
    try:
        await callback.bot.send_message(
            tid,
            t.RECEIPT_APPROVED.format(balance=new_balance),
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("order:no:"))
async def order_reject(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.status != OrderStatus.PENDING.value:
            await callback.answer("سفارش معتبر نیست.", show_alert=True)
            return
        order.status = OrderStatus.REJECTED.value
        user = await session.get(BotUser, order.user_id)
        tid = user.telegram_id
        await session.commit()

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ رد شد توسط ادمین",
    )
    await callback.answer("رد شد")
    try:
        await callback.bot.send_message(
            tid,
            t.RECEIPT_REJECTED.format(reason="توسط ادمین رد شد"),
        )
    except Exception:
        pass


# ==================== User Management ====================
@router.message(F.text == t.BTN_USERS)
async def users_handler(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    if not is_admin(message.from_user.id, user.is_admin):
        await message.answer(t.NOT_ADMIN)
        return
    await state.set_state(UserManageStates.waiting_query)
    await message.answer(t.USER_SEARCH, reply_markup=cancel_keyboard())


@router.callback_query(F.data == "admin:users")
async def admin_users_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserManageStates.waiting_query)
    await callback.message.edit_text(t.USER_SEARCH, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(UserManageStates.waiting_query)
async def user_query_received(message: Message, state: FSMContext):
    q = message.text.strip()
    target = await get_user_by_id_or_username(q)
    if not target:
        await message.answer(t.USER_NOT_FOUND)
        return
    await state.clear()
    status = "🚫 مسدود" if target.status == "blocked" else "✅ فعال"
    text = t.USER_INFO.format(
        telegram_id=target.telegram_id,
        name=target.full_name or "-",
        username=target.username or "-",
        balance=target.balance,
        status=status,
        created=target.created_at.strftime("%Y-%m-%d") if target.created_at else "-",
    )
    await message.answer(text, reply_markup=user_manage_keyboard(target.telegram_id))


@router.callback_query(F.data.startswith("u:charge:"))
async def u_charge(callback: CallbackQuery, state: FSMContext):
    tid = int(callback.data.split(":")[2])
    await state.update_data(target_tid=tid)
    await state.set_state(UserManageStates.waiting_charge_amount)
    await callback.message.answer("مبلغ شارژ (تومان) را وارد کنید:")
    await callback.answer()


@router.message(UserManageStates.waiting_charge_amount)
async def u_charge_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip().replace(",", ""))
    except ValueError:
        await message.answer("❌ عدد نامعتبر")
        return
    data = await state.get_data()
    tid = data["target_tid"]
    await state.clear()
    async with async_session() as session:
        result = await session.execute(select(BotUser).where(BotUser.telegram_id == tid))
        u = result.scalar_one_or_none()
        if not u:
            await message.answer(t.USER_NOT_FOUND)
            return
        u.balance += amount
        await session.commit()
        new_bal = u.balance
    await message.answer(f"✅ {amount:,} تومان اضافه شد.\nموجودی جدید: {new_bal:,}")


@router.callback_query(F.data.startswith("u:zero:"))
async def u_zero(callback: CallbackQuery):
    tid = int(callback.data.split(":")[2])
    async with async_session() as session:
        result = await session.execute(select(BotUser).where(BotUser.telegram_id == tid))
        u = result.scalar_one_or_none()
        if u:
            u.balance = 0
            await session.commit()
    await callback.answer("موجودی صفر شد ✅", show_alert=True)


@router.callback_query(F.data.startswith("u:block:"))
async def u_block(callback: CallbackQuery):
    tid = int(callback.data.split(":")[2])
    async with async_session() as session:
        result = await session.execute(select(BotUser).where(BotUser.telegram_id == tid))
        u = result.scalar_one_or_none()
        if u:
            u.status = "blocked"
            await session.commit()
    await callback.answer("کاربر مسدود شد 🚫", show_alert=True)


@router.callback_query(F.data.startswith("u:unblock:"))
async def u_unblock(callback: CallbackQuery):
    tid = int(callback.data.split(":")[2])
    async with async_session() as session:
        result = await session.execute(select(BotUser).where(BotUser.telegram_id == tid))
        u = result.scalar_one_or_none()
        if u:
            u.status = "active"
            await session.commit()
    await callback.answer("مسدودی رفع شد ✅", show_alert=True)


@router.callback_query(F.data.startswith("u:msg:"))
async def u_msg(callback: CallbackQuery, state: FSMContext):
    tid = int(callback.data.split(":")[2])
    await state.update_data(target_tid=tid)
    await state.set_state(UserManageStates.waiting_message)
    await callback.message.answer("پیام خود را بنویسید:")
    await callback.answer()


@router.message(UserManageStates.waiting_message)
async def u_send_msg(message: Message, state: FSMContext):
    data = await state.get_data()
    tid = data["target_tid"]
    await state.clear()
    try:
        await message.bot.send_message(tid, f"📩 پیام از پشتیبانی:\n\n{message.text}")
        await message.answer("✅ پیام ارسال شد.")
    except Exception as e:
        await message.answer(f"❌ ارسال نشد: {e}")


@router.callback_query(F.data.startswith("u:services:"))
async def u_services(callback: CallbackQuery):
    tid = int(callback.data.split(":")[2])
    async with async_session() as session:
        result = await session.execute(select(BotUser).where(BotUser.telegram_id == tid))
        u = result.scalar_one_or_none()
        if not u:
            await callback.answer(t.USER_NOT_FOUND, show_alert=True)
            return
        result = await session.execute(
            select(Service).where(Service.owner_id == u.id).order_by(Service.created_at.desc())
        )
        services = list(result.scalars().all())

    if not services:
        await callback.answer("سرویسی ندارد.", show_alert=True)
        return
    lines = [f"📦 سرویس‌های {tid}:\n"]
    for s in services[:15]:
        st = "✅" if s.is_active else "❌"
        lines.append(f"{st} <code>{s.username}</code> | {s.password or '-'}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


# ==================== Placeholders ====================
@router.message(F.text == t.BTN_BROADCAST)
async def broadcast_ph(message: Message):
    await message.answer("📢 پیام همگانی در آپدیت بعدی کامل می‌شود.")


@router.message(F.text == t.BTN_TEXTS)
async def texts_ph(message: Message):
    await message.answer("📝 تغییر متون در آپدیت بعدی.")


@router.message(F.text == t.BTN_BACKUP)
async def backup_handler(message: Message):
    from utils.backup import create_backup_zip, send_backup_to_admins
    from aiogram.types import FSInputFile
    await message.answer("⏳ در حال ساخت بکاپ...")
    try:
        path = await asyncio.to_thread(create_backup_zip)
        await message.answer_document(
            FSInputFile(path),
            caption=f"💾 بکاپ دستی ROBIXA\n<code>{path.name}</code>",
        )
        # also try send to other admins
        try:
            await send_backup_to_admins(message.bot, chat_ids=None)
        except Exception:
            pass
    except Exception as e:
        await message.answer(f"❌ خطا در بکاپ: {e}")


@router.message(F.text.startswith("/setbalance"))
async def set_balance_cmd(message: Message):
    user = await get_or_create_user(message.from_user.id)
    if not is_admin(message.from_user.id, user.is_admin):
        await message.answer(t.NOT_ADMIN)
        return
    parts = message.text.strip().split()
    if len(parts) != 3:
        await message.answer("فرمت: <code>/setbalance TELEGRAM_ID AMOUNT</code>")
        return
    try:
        target_id = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        await message.answer("❌ عدد نامعتبر")
        return
    async with async_session() as session:
        result = await session.execute(select(BotUser).where(BotUser.telegram_id == target_id))
        target = result.scalar_one_or_none()
        if not target:
            await message.answer("❌ کاربر یافت نشد.")
            return
        target.balance = amount
        await session.commit()
    await message.answer(f"✅ موجودی {target_id} = {amount:,} تومان")
