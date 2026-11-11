import random
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from config import settings
from database.db import (
    get_or_create_user, get_active_products, get_product, get_panel,
    async_session, get_setting, get_active_cards,
)
from database.models import Service, Order, OrderStatus, PaymentMethod
from keyboards.menus import (
    product_list_keyboard, confirm_buy_keyboard, support_keyboard,
    wallet_keyboard, charge_methods_keyboard, cancel_keyboard,
    approve_reject_keyboard,
)
from texts import fa as t
from utils.generators import generate_username, generate_password, generate_test_username
from panels.factory import create_user_on_panel, PanelError
from payments.zarinpal import Zarinpal, ZarinpalError

router = Router()


class ChargeStates(StatesGroup):
    waiting_amount = State()
    waiting_receipt = State()


# ---------- Support ----------
@router.message(F.text == t.BTN_SUPPORT)
async def support_handler(message: Message):
    support = await get_setting("support_username", settings.SUPPORT_USERNAME)
    text = t.SUPPORT_TEXT.format(support=support)
    await message.answer(text, reply_markup=support_keyboard(support))


# ---------- Wallet ----------
@router.message(F.text == t.BTN_WALLET)
async def wallet_handler(message: Message):
    user = await get_or_create_user(message.from_user.id)
    text = t.WALLET_INFO.format(balance=user.balance)
    await message.answer(text, reply_markup=wallet_keyboard())


@router.callback_query(F.data == "wallet:back")
async def wallet_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(callback.from_user.id)
    text = t.WALLET_INFO.format(balance=user.balance)
    await callback.message.edit_text(text, reply_markup=wallet_keyboard())
    await callback.answer()


@router.callback_query(F.data == "wallet:charge")
async def wallet_charge(callback: CallbackQuery, state: FSMContext):
    card_on = (await get_setting("card_enabled", "0")) == "1"
    zarin_on = (await get_setting("zarinpal_enabled", "0")) == "1"
    stars_on = (await get_setting("stars_enabled", "0")) == "1"
    await callback.message.edit_text(
        t.CHARGE_METHODS,
        reply_markup=charge_methods_keyboard(card_on, zarin_on, stars_on),
    )
    await callback.answer()


@router.callback_query(F.data == "pay:card")
async def pay_card_start(callback: CallbackQuery, state: FSMContext):
    cards = await get_active_cards()
    if not cards:
        await callback.answer("هیچ کارتی تعریف نشده است.", show_alert=True)
        return
    await state.set_state(ChargeStates.waiting_amount)
    await callback.message.edit_text(
        "مبلغ شارژ را به تومان وارد کنید:\nمثال: 100000",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(ChargeStates.waiting_amount)
async def charge_amount_received(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip().replace(",", ""))
    except ValueError:
        await message.answer("❌ مبلغ باید عدد باشد.")
        return

    min_a = int(await get_setting("card_min", "10000"))
    max_a = int(await get_setting("card_max", "50000000"))
    if amount < min_a or amount > max_a:
        await message.answer(f"❌ مبلغ باید بین {min_a:,} و {max_a:,} تومان باشد.")
        return

    data = await state.get_data()
    pay_method = data.get("pay_method", "card")
    user = await get_or_create_user(message.from_user.id)

    # ----- Zarinpal branch -----
    if pay_method == "zarinpal":
        merchant = await get_setting("zarinpal_merchant", "")
        sandbox = (await get_setting("zarinpal_sandbox", "1")) == "1"
        zp = Zarinpal(merchant_id=merchant, sandbox=sandbox, callback_url="https://t.me/")
        try:
            result = await zp.request_payment(
                amount_toman=amount,
                description=f"ROBIXA charge user {user.telegram_id}",
            )
        except ZarinpalError as e:
            await message.answer(f"❌ خطا زرین‌پال: {e.message}")
            await state.clear()
            return
        except Exception as e:
            await message.answer(f"❌ خطا: {e}")
            await state.clear()
            return

        async with async_session() as session:
            order = Order(
                user_id=user.id,
                amount=amount,
                status=OrderStatus.PENDING.value,
                payment_method=PaymentMethod.ZARINPAL.value,
                tracking_code=result["authority"],
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)
            order_id = order.id

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="💳 پرداخت در زرین‌پال", url=result["payment_url"]))
        b.row(InlineKeyboardButton(text="✅ پرداخت کردم — تأیید", callback_data=f"zp:check:{order_id}"))
        b.row(InlineKeyboardButton(text="❌ انصراف", callback_data="cancel"))
        await state.clear()
        await message.answer(
            f"مبلغ: <b>{amount:,}</b> تومان\n"
            f"روی دکمه پرداخت بزنید، پس از پرداخت «پرداخت کردم» را بزنید.",
            reply_markup=b.as_markup(),
        )
        return

    # ----- Card branch -----
    security_on = (await get_setting("card_security", "1")) == "1"
    security_extra = random.randint(127, 799) if security_on else 0
    final_amount = amount + security_extra
    cards = await get_active_cards()
    if not cards:
        await message.answer("❌ کارتی تعریف نشده.")
        await state.clear()
        return
    random_mode = (await get_setting("card_random", "1")) == "1"
    card = random.choice(cards) if random_mode else cards[0]

    async with async_session() as session:
        order = Order(
            user_id=user.id,
            amount=amount,
            status=OrderStatus.PENDING.value,
            payment_method=PaymentMethod.CARD.value,
            security_amount=final_amount,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        order_id = order.id

    bank = f"\n🏦 بانک: {card.bank_name}" if card.bank_name else ""
    security_note = t.SECURITY_NOTE if security_on else ""
    text_msg = t.CARD_PAYMENT_INFO.format(
        amount=final_amount,
        security_note=security_note,
        card_number=card.card_number,
        card_holder=card.card_holder,
        bank=bank,
    )
    await state.update_data(order_id=order_id, final_amount=final_amount)
    await state.set_state(ChargeStates.waiting_receipt)
    await message.answer(text_msg)
    await message.answer(t.SEND_RECEIPT, reply_markup=cancel_keyboard())


@router.message(ChargeStates.waiting_receipt, F.photo)
async def receipt_received(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await message.answer(t.ERROR_GENERIC)
        await state.clear()
        return

    file_id = message.photo[-1].file_id
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            await message.answer(t.ERROR_GENERIC)
            await state.clear()
            return
        order.receipt_file_id = file_id
        await session.commit()

    await state.clear()
    await message.answer(t.RECEIPT_RECEIVED)

    # Notify admins
    from aiogram import Bot
    bot: Bot = message.bot
    user = await get_or_create_user(message.from_user.id)
    caption = (
        f"💳 رسید جدید\n\n"
        f"کاربر: {user.full_name or '-'} (@{user.username or '-'})\n"
        f"آیدی: <code>{user.telegram_id}</code>\n"
        f"مبلغ درخواستی: {order.amount:,}\n"
        f"مبلغ امنیتی: {order.security_amount:,}\n"
        f"سفارش: #{order.id}"
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_photo(
                admin_id,
                photo=file_id,
                caption=caption,
                reply_markup=approve_reject_keyboard(order.id),
            )
        except Exception:
            pass


@router.message(ChargeStates.waiting_receipt)
async def receipt_not_photo(message: Message):
    await message.answer("لطفاً فقط عکس رسید را ارسال کنید.")


# ---------- Buy ----------
@router.message(F.text == t.BTN_BUY)
async def buy_handler(message: Message):
    products = await get_active_products()
    if not products:
        await message.answer("⚠️ در حال حاضر محصولی برای فروش وجود ندارد.")
        return
    await message.answer(t.SELECT_PRODUCT, reply_markup=product_list_keyboard(products))


@router.callback_query(F.data.startswith("buy:"))
async def product_selected(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    product = await get_product(product_id)
    if not product or not product.is_active:
        await callback.answer("محصول یافت نشد.", show_alert=True)
        return
    data_text = "نامحدود ∞" if product.data_limit_gb == 0 else f"{product.data_limit_gb} گیگابایت"
    text = t.PRODUCT_INFO.format(
        name=product.name, price=product.price, data=data_text, days=product.days,
    )
    await callback.message.edit_text(text, reply_markup=confirm_buy_keyboard(product.id))
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_buy:"))
async def confirm_buy(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    product = await get_product(product_id)
    if not product:
        await callback.answer("محصول یافت نشد.", show_alert=True)
        return

    user = await get_or_create_user(callback.from_user.id)
    if user.balance < product.price:
        await callback.answer(t.INSUFFICIENT_BALANCE.format(balance=user.balance), show_alert=True)
        return

    panel = await get_panel(product.panel_id)
    if not panel or not panel.is_active:
        await callback.answer("پنل مربوطه در دسترس نیست.", show_alert=True)
        return

    username = generate_username()
    password = generate_password()

    try:
        await create_user_on_panel(
            panel_type=panel.panel_type,
            base_url=panel.base_url,
            username=username,
            data_limit_gb=product.data_limit_gb,
            days=product.days,
            panel_username=panel.username,
            panel_password=panel.password,
            token=panel.api_token,
            note=f"ROBIXA | TG:{user.telegram_id} | {product.name}",
        )
    except PanelError as e:
        await callback.message.edit_text(f"❌ خطا در ساخت اکانت:\n<code>{e.message}</code>")
        await callback.answer()
        return
    except Exception as e:
        await callback.message.edit_text(f"❌ خطای غیرمنتظره:\n<code>{e}</code>")
        await callback.answer()
        return

    expire_at = None
    if product.days > 0:
        expire_at = datetime.now(timezone.utc) + timedelta(days=product.days)

    async with async_session() as session:
        db_user = await session.get(type(user), user.id)
        db_user.balance -= product.price
        service = Service(
            owner_id=user.id,
            panel_id=panel.id,
            product_id=product.id,
            username=username,
            password=password,
            is_test=False,
            is_active=True,
            data_limit_gb=product.data_limit_gb,
            expire_at=expire_at,
        )
        session.add(service)
        await session.commit()

    expire_text = expire_at.strftime("%Y-%m-%d %H:%M") if expire_at else "نامحدود ∞"
    text = t.SERVICE_CREATED.format(
        username=username, password=password, panel_url=panel.base_url,
        product_name=product.name, expire=expire_text,
    )
    await callback.message.edit_text(text)
    await callback.answer("✅ خرید موفق!")


# ---------- Test ----------
@router.message(F.text == t.BTN_TEST)
async def test_account_handler(message: Message):
    user = await get_or_create_user(message.from_user.id)
    from database.db import get_active_panels
    panels = await get_active_panels()
    test_panel = next((p for p in panels if p.test_enabled), None)
    if not test_panel:
        await message.answer("⚠️ امکان دریافت اکانت تست وجود ندارد.")
        return

    async with async_session() as session:
        result = await session.execute(
            select(Service)
            .where(Service.owner_id == user.id, Service.is_test == True)
            .order_by(Service.created_at.desc())
            .limit(1)
        )
        last_test = result.scalar_one_or_none()
        if last_test and test_panel.test_limit_days > 0:
            delta = datetime.now(timezone.utc) - last_test.created_at.replace(tzinfo=timezone.utc)
            if delta.days < test_panel.test_limit_days:
                await message.answer(t.TEST_ALREADY_USED)
                return

    username = generate_test_username()
    password = generate_password()
    try:
        await create_user_on_panel(
            panel_type=test_panel.panel_type,
            base_url=test_panel.base_url,
            username=username,
            data_limit_gb=test_panel.test_data_limit_gb,
            days=test_panel.test_days,
            panel_username=test_panel.username,
            panel_password=test_panel.password,
            token=test_panel.api_token,
            note=f"TEST | TG:{user.telegram_id}",
        )
    except Exception as e:
        await message.answer(f"❌ خطا در ساخت اکانت تست:\n<code>{e}</code>")
        return

    expire_at = datetime.now(timezone.utc) + timedelta(days=test_panel.test_days)
    async with async_session() as session:
        service = Service(
            owner_id=user.id,
            panel_id=test_panel.id,
            username=username,
            password=password,
            is_test=True,
            is_active=True,
            data_limit_gb=test_panel.test_data_limit_gb,
            expire_at=expire_at,
        )
        session.add(service)
        await session.commit()

    data_text = "نامحدود" if test_panel.test_data_limit_gb == 0 else str(test_panel.test_data_limit_gb)
    text = t.TEST_CREATED.format(
        username=username, password=password,
        days=test_panel.test_days, data=data_text,
    )
    await message.answer(text)


# ---------- My Services ----------
@router.message(F.text == t.BTN_MY_SERVICES)
async def my_services_handler(message: Message):
    user = await get_or_create_user(message.from_user.id)
    async with async_session() as session:
        result = await session.execute(
            select(Service).where(Service.owner_id == user.id).order_by(Service.created_at.desc())
        )
        services = list(result.scalars().all())

    if not services:
        await message.answer("📦 شما هنوز سرویسی ندارید.")
        return

    lines = ["📦 <b>سرویس‌های شما:</b>\n"]
    for s in services[:20]:
        status = "✅ فعال" if s.is_active else "❌ منقضی/غیرفعال"
        test_tag = " [تست]" if s.is_test else ""
        expire = s.expire_at.strftime("%Y-%m-%d") if s.expire_at else "∞"
        lines.append(
            f"• <code>{s.username}</code>{test_tag}\n"
            f"  🔑 <code>{s.password or '-'}</code>\n"
            f"  {status} | انقضا: {expire}\n"
        )
    await message.answer("\n".join(lines))


@router.callback_query(F.data == "pay:zarinpal")
async def pay_zarinpal_start(callback: CallbackQuery, state: FSMContext):
    merchant = await get_setting("zarinpal_merchant", "")
    if not merchant or (await get_setting("zarinpal_enabled", "0")) != "1":
        await callback.answer("زرین‌پال فعال نیست.", show_alert=True)
        return
    await state.set_state(ChargeStates.waiting_amount)
    await state.update_data(pay_method="zarinpal")
    await callback.message.edit_text(
        "مبلغ شارژ (تومان) را وارد کنید:\nمثال: 100000",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("zp:check:"))
async def zarinpal_check(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.status != OrderStatus.PENDING.value:
            await callback.answer("سفارش معتبر نیست.", show_alert=True)
            return
        authority = order.tracking_code
        amount = order.amount
        user_id = order.user_id

    if not authority:
        await callback.answer("کد authority موجود نیست.", show_alert=True)
        return

    merchant = await get_setting("zarinpal_merchant", "")
    sandbox = (await get_setting("zarinpal_sandbox", "1")) == "1"
    zp = Zarinpal(merchant_id=merchant, sandbox=sandbox)
    try:
        result = await zp.verify_payment(amount_toman=amount, authority=authority)
    except ZarinpalError as e:
        await callback.answer(f"پرداخت تأیید نشد: {e.message}", show_alert=True)
        return
    except Exception as e:
        await callback.answer(f"خطا: {e}", show_alert=True)
        return

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order or order.status != OrderStatus.PENDING.value:
            await callback.answer("قبلاً پردازش شده.", show_alert=True)
            return
        from database.models import BotUser
        u = await session.get(BotUser, user_id)
        if not u:
            await callback.answer("کاربر یافت نشد.", show_alert=True)
            return
        u.balance += order.amount
        order.status = OrderStatus.COMPLETED.value
        order.completed_at = datetime.now(timezone.utc)
        order.admin_note = f"ref={result.get('ref_id')}"
        await session.commit()
        new_bal = u.balance

    await callback.message.edit_text(
        f"✅ پرداخت زرین‌پال موفق\nکد پیگیری: <code>{result.get('ref_id')}</code>\n"
        f"موجودی جدید: <b>{new_bal:,}</b> تومان"
    )
    await callback.answer("تأیید شد")

