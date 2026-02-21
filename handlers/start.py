from aiogram import F, Router
from aiogram.filters import CommandStart

from handlers.utils import safe_edit_text
from aiogram.types import CallbackQuery, Message

from keyboards import get_mode_keyboard

router = Router(name="start")

GREETING = (
    "Привет! Я бот для поиска команды на гейм-джем.\n\n"
    "Выбери, что ты ищешь:"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(GREETING, reply_markup=get_mode_keyboard())


@router.callback_query(F.data == "start")
async def callback_start(callback: CallbackQuery) -> None:
    await safe_edit_text(callback.message, GREETING, reply_markup=get_mode_keyboard())
    await callback.answer()
