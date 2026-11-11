from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from config import settings
from database.db import get_or_create_user
from keyboards.menus import main_menu, admin_menu
from texts import fa as t

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    if user.status == "blocked":
        await message.answer(t.USER_BLOCKED)
        return
    name = message.from_user.first_name or "کاربر"
    await message.answer(
        t.WELCOME.format(name=name),
        reply_markup=main_menu(is_admin=user.is_admin),
    )


@router.message(F.text == t.BTN_BACK)
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(t.MAIN_MENU_USER, reply_markup=main_menu(is_admin=user.is_admin))


@router.message(F.text == t.BTN_ADMIN)
async def open_admin(message: Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    if not user.is_admin and message.from_user.id not in settings.admin_ids:
        await message.answer(t.NOT_ADMIN)
        return
    name = message.from_user.first_name or "ادمین"
    text = t.ADMIN_WELCOME.format(version=settings.BOT_VERSION, name=name)
    await message.answer(text, reply_markup=admin_menu())


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(t.CANCELLED)
    await callback.answer()


@router.callback_query(F.data == "user:main")
async def user_main_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(callback.from_user.id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        t.MAIN_MENU_USER,
        reply_markup=main_menu(is_admin=user.is_admin),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:back")
async def admin_back_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    name = callback.from_user.first_name or "ادمین"
    text = t.ADMIN_WELCOME.format(version=settings.BOT_VERSION, name=name)
    await callback.message.answer(text, reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_cb(callback: CallbackQuery):
    await callback.answer()
