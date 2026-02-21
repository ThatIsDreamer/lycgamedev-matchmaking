import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.states import SoloForm
from keyboards import (
    get_age_keyboard,
    get_participation_format_keyboard,
    get_specialty_keyboard,
    get_team_card_keyboard,
)
from keyboards.inline import ROLES
from storage import (
    create_request,
    get_active_teams,
    get_invite,
    get_request_by_solo_and_team,
    get_team,
    get_user,
    save_user,
    set_user_active,
    update_invite_status,
)
from handlers.utils import safe_edit_text

router = Router(name="solo")


def _solo_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    user = get_user(user_id)
    is_active = user.get("is_active", True) if user else True
    rows = [
        [InlineKeyboardButton(text="Смотреть команды", callback_data="solo:browse:0")],
    ]
    if is_active:
        rows.append([InlineKeyboardButton(text="Закрыть анкету", callback_data="solo:close_profile")])
    else:
        rows.append([InlineKeyboardButton(text="Открыть анкету снова", callback_data="solo:open_profile")])
    rows.append([InlineKeyboardButton(text="В главное меню", callback_data="start")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _inline_btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


@router.callback_query(F.data == "mode:solo")
async def mode_solo(callback: CallbackQuery, state: FSMContext) -> None:
    user = get_user(callback.from_user.id)
    if user:
        await state.clear()
        await safe_edit_text(
            callback.message,
            "Профиль сохранён! Ты можешь просматривать команды и отправлять заявки.",
            reply_markup=_solo_menu_keyboard(callback.from_user.id),
        )
        await callback.answer()
        return
    await state.set_state(SoloForm.display_name)
    await safe_edit_text(
        callback.message,
        "Как к тебе обращаться? (имя или ник)",
    )
    await callback.answer()


@router.message(SoloForm.display_name, F.text)
async def solo_display_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Введи имя или ник (минимум 2 символа).")
        return
    await state.update_data(display_name=name)
    await state.set_state(SoloForm.age_category)
    await message.answer("Возрастная категория:", reply_markup=get_age_keyboard())


@router.callback_query(SoloForm.age_category, F.data.startswith("age:"))
async def solo_age(callback: CallbackQuery, state: FSMContext) -> None:
    age = callback.data.split(":")[-1]
    await state.update_data(age_category=age)
    await state.set_state(SoloForm.participation_format)
    await callback.message.edit_text("Формат участия:", reply_markup=get_participation_format_keyboard())
    await callback.answer()


@router.callback_query(SoloForm.participation_format, F.data.startswith("format:"))
async def solo_format(callback: CallbackQuery, state: FSMContext) -> None:
    fmt = callback.data.split(":")[-1]
    await state.update_data(participation_format=fmt)
    await state.set_state(SoloForm.specialty)
    await callback.message.edit_text("Специальность:", reply_markup=get_specialty_keyboard())
    await callback.answer()


@router.callback_query(SoloForm.specialty, F.data.startswith("specialty:"))
async def solo_specialty(callback: CallbackQuery, state: FSMContext) -> None:
    specialty = callback.data.split(":")[-1]
    await state.update_data(specialty=specialty)
    await state.set_state(SoloForm.description)
    await callback.message.edit_text(
        "Опиши свой опыт и портфолио: навыки, проекты, в чём хочешь участвовать. "
        "Это поможет командам тебя найти."
    )
    await callback.answer()


@router.message(SoloForm.description, F.text)
async def solo_description(message: Message, state: FSMContext) -> None:
    description = message.text.strip()
    if len(description) < 10:
        await message.answer("Пожалуйста, напиши развёрнутое описание (минимум 10 символов).")
        return
    data = await state.get_data()
    save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        display_name=data.get("display_name", message.from_user.username or ""),
        age_category=data.get("age_category", "18+"),
        participation_format=data.get("participation_format", "online"),
        specialty=data.get("specialty", "other"),
        description=description,
    )
    await state.clear()
    await message.answer(
        "Профиль сохранён! Теперь ты можешь просматривать команды и отправлять заявки.",
        reply_markup=_solo_menu_keyboard(message.from_user.id),
    )


@router.callback_query(F.data == "solo:close_profile")
async def solo_close_profile(callback: CallbackQuery, state: FSMContext) -> None:
    set_user_active(callback.from_user.id, False)
    await safe_edit_text(
        callback.message,
        "Анкета закрыта. Ты не показываешься в поиске команд.",
        reply_markup=_solo_menu_keyboard(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data == "solo:open_profile")
async def solo_open_profile(callback: CallbackQuery, state: FSMContext) -> None:
    set_user_active(callback.from_user.id, True)
    await safe_edit_text(
        callback.message,
        "Анкета снова активна. Тебя видят команды в поиске.",
        reply_markup=_solo_menu_keyboard(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("solo:browse:"))
async def solo_browse(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    page = int(callback.data.split(":")[-1])
    active = get_active_teams()
    total = len(active)
    if total == 0:
        await safe_edit_text(
            callback.message,
            "Пока нет активных команд в поиске. Загляни позже!",
            reply_markup=_solo_menu_keyboard(callback.from_user.id),
        )
        await callback.answer()
        return
    page = max(0, min(page, total - 1))
    key, team = active[page]
    owner_id = team["owner_id"]
    team_name = team.get("team_name", "")
    team_number = team.get("team_number")
    display_name = team_name or (f"Команда #{team_number}" if team_number else "Команда")
    desc = team.get("description", "")
    roles_labels = [ROLES.get(r, r) for r in team.get("roles_needed", [])]
    roles_str = ", ".join(roles_labels) if roles_labels else "—"
    pitch = team.get("pitch_format", "online")
    pitch_str = "Онлайн" if pitch == "online" else "Офлайн"
    text = f"<b>{html.escape(display_name)}</b> (страница {page + 1}/{total})\n\n{html.escape(desc)}\n\n<b>Ищут:</b> {roles_str}\n<b>Питчинг:</b> {pitch_str}"
    kb = get_team_card_keyboard(team_owner_id=owner_id, page=page, total=total)
    kb.inline_keyboard.append([_inline_btn("В меню", "start")])
    await safe_edit_text(callback.message, text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("browse:"))
async def browse_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    active = get_active_teams()
    total = len(active)
    if total == 0:
        await safe_edit_text(
            callback.message,
            "Пока нет активных команд в поиске.",
            reply_markup=_solo_menu_keyboard(callback.from_user.id),
        )
        await callback.answer()
        return
    page = max(0, min(page, total - 1))
    key, team = active[page]
    owner_id = team["owner_id"]
    team_name = team.get("team_name", "")
    team_number = team.get("team_number")
    display_name = team_name or (f"Команда #{team_number}" if team_number else "Команда")
    desc = team.get("description", "")
    roles_labels = [ROLES.get(r, r) for r in team.get("roles_needed", [])]
    roles_str = ", ".join(roles_labels) if roles_labels else "—"
    pitch = team.get("pitch_format", "online")
    pitch_str = "Онлайн" if pitch == "online" else "Офлайн"
    text = f"<b>{html.escape(display_name)}</b> (страница {page + 1}/{total})\n\n{html.escape(desc)}\n\n<b>Ищут:</b> {roles_str}\n<b>Питчинг:</b> {pitch_str}"
    kb = get_team_card_keyboard(team_owner_id=owner_id, page=page, total=total)
    kb.inline_keyboard.append([_inline_btn("В меню", "start")])
    await safe_edit_text(callback.message, text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("request:"))
async def send_request(callback: CallbackQuery, state: FSMContext) -> None:
    team_owner_id = int(callback.data.split(":")[-1])
    solo_id = callback.from_user.id
    existing = get_request_by_solo_and_team(solo_id, team_owner_id)
    if existing and existing.get("status") == "pending":
        await callback.answer("Ты уже отправил заявку этой команде.", show_alert=True)
        return
    user = get_user(solo_id)
    if not user:
        await callback.answer("Сначала заполни профиль (/start → Ищу команду).", show_alert=True)
        return
    request_id = create_request(solo_id, team_owner_id)
    if not request_id:
        await callback.answer("Заявка уже существует.", show_alert=True)
        return
    from keyboards import get_request_keyboard
    team = get_team(team_owner_id)
    if team:
        display_name = user.get("display_name") or user.get("username") or "без имени"
        desc = user.get("description", "")
        await callback.bot.send_message(
            team_owner_id,
            f"Новая заявка от {html.escape(display_name)} (@{callback.from_user.username or 'без username'})\n\n{html.escape(desc)}",
            reply_markup=get_request_keyboard(request_id),
        )
    await callback.answer("Заявка отправлена!")
    await callback.message.edit_text(
        "Заявка отправлена! Команда получит уведомление.",
        reply_markup=_solo_menu_keyboard(callback.from_user.id),
    )


@router.callback_query(F.data.startswith("invite_accept:"))
async def solo_invite_accept(callback: CallbackQuery, state: FSMContext) -> None:
    invite_id = callback.data.split(":")[-1]
    inv = get_invite(invite_id)
    if not inv or inv.get("status") != "pending":
        await callback.answer("Приглашение уже обработано.", show_alert=True)
        return
    if inv["solo_id"] != callback.from_user.id:
        await callback.answer("Это не твоё приглашение.", show_alert=True)
        return
    update_invite_status(invite_id, "accepted")
    team = get_team(inv["team_owner_id"])
    team_name = team.get("team_name") or f"Команда #{team.get('team_number', '?')}" if team else "Команда"
    solo = get_user(callback.from_user.id)
    username = solo.get("username", "") if solo else ""
    contact = f"@{username}" if username else f"ID: {callback.from_user.id}"
    await callback.bot.send_message(
        inv["team_owner_id"],
        f"Пользователь {contact} принял приглашение в команду.",
    )
    await callback.message.edit_text(
        f"Ты принял приглашение команды «{html.escape(team_name)}». Свяжутся с тобой."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("invite_deny:"))
async def solo_invite_deny(callback: CallbackQuery, state: FSMContext) -> None:
    invite_id = callback.data.split(":")[-1]
    inv = get_invite(invite_id)
    if not inv or inv.get("status") != "pending":
        await callback.answer("Приглашение уже обработано.", show_alert=True)
        return
    if inv["solo_id"] != callback.from_user.id:
        await callback.answer("Это не твоё приглашение.", show_alert=True)
        return
    update_invite_status(invite_id, "denied")
    await callback.bot.send_message(
        inv["team_owner_id"],
        "Пользователь отклонил приглашение в команду.",
    )
    await callback.message.edit_text("Ты отклонил приглашение.")
    await callback.answer()
