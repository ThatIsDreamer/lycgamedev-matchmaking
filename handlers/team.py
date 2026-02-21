import html

from aiogram import F, Router

from handlers.utils import safe_edit_text
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.states import TeamForm
from keyboards import (
    get_pitch_format_keyboard,
    get_request_keyboard,
    get_roles_keyboard,
    get_solo_card_keyboard,
    get_specialty_filter_keyboard,
    get_team_dashboard_keyboard,
)
from keyboards.inline import PARTICIPATION_FORMATS, ROLES, SPECIALTIES
from storage import (
    create_invite,
    delete_team,
    get_active_users_by_specialty,
    get_pending_requests,
    get_request,
    get_team,
    get_user,
    save_team,
    toggle_team_pause,
    update_request_status,
)

router = Router(name="team")


@router.callback_query(F.data == "mode:team")
async def mode_team(callback: CallbackQuery, state: FSMContext) -> None:
    team = get_team(callback.from_user.id)
    if team:
        await state.clear()
        is_paused = team.get("is_paused", False)
        team_name = team.get("team_name", "")
        team_number = team.get("team_number")
        display_name = team_name or (f"Команда #{team_number}" if team_number else "Команда")
        desc = team.get("description", "")
        roles_labels = [ROLES.get(r, r) for r in team.get("roles_needed", [])]
        roles_str = ", ".join(roles_labels) if roles_labels else "—"
        pitch = team.get("pitch_format", "online")
        pitch_str = "Онлайн" if pitch == "online" else "Офлайн"
        title = f"<b>{html.escape(display_name)}</b>"
        await safe_edit_text(
            callback.message,
            f"{title}\n\n{html.escape(desc)}\n\n<b>Ищете:</b> {roles_str}\n<b>Питчинг:</b> {pitch_str}\n\nСтатус: {'поиск закрыт' if is_paused else 'в поиске'}",
            reply_markup=_team_menu_keyboard(callback.from_user.id, is_paused),
        )
        await callback.answer()
        return
    await state.set_state(TeamForm.team_name)
    from keyboards import get_team_name_skip_keyboard
    await safe_edit_text(
        callback.message,
        "Как называется ваша команда? (короткое название или «Без названия»)",
        reply_markup=get_team_name_skip_keyboard(),
    )
    await callback.answer()


@router.callback_query(TeamForm.team_name, F.data == "team_name:skip")
async def team_name_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(team_name="")
    await state.set_state(TeamForm.pitch_format)
    await callback.message.edit_text("Формат питчинга команды:", reply_markup=get_pitch_format_keyboard())
    await callback.answer()


@router.message(TeamForm.team_name, F.text)
async def team_name(message: Message, state: FSMContext) -> None:
    team_name = message.text.strip()
    if len(team_name) < 2:
        await message.answer("Введи название (минимум 2 символа) или нажми «Без названия» в предыдущем сообщении.")
        return
    await state.update_data(team_name=team_name)
    await state.set_state(TeamForm.pitch_format)
    await message.answer("Формат питчинга команды:", reply_markup=get_pitch_format_keyboard())


@router.callback_query(TeamForm.pitch_format, F.data.startswith("pitch:"))
async def team_pitch_format(callback: CallbackQuery, state: FSMContext) -> None:
    pitch = callback.data.split(":")[-1]
    await state.update_data(pitch_format=pitch)
    await state.set_state(TeamForm.description)
    await callback.message.edit_text(
        "Опиши вашу команду: концепцию, стиль, чем занимаетесь. "
        "Это поможет участникам понять, подходят ли вы друг другу."
    )
    await callback.answer()


@router.message(TeamForm.description, F.text)
async def team_description(message: Message, state: FSMContext) -> None:
    description = message.text.strip()
    if len(description) < 10:
        await message.answer("Пожалуйста, напиши развёрнутое описание (минимум 10 символов).")
        return
    await state.update_data(description=description)
    await state.set_state(TeamForm.roles)
    await message.answer(
        "Выбери роли, которые нужны команде (можно несколько):",
        reply_markup=get_roles_keyboard([]),
    )


@router.callback_query(TeamForm.roles, F.data.startswith("role:"))
async def team_role_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    role_id = callback.data.split(":")[-1]
    data = await state.get_data()
    selected: list = list(data.get("roles", []))
    if role_id in selected:
        selected.remove(role_id)
    else:
        selected.append(role_id)
    await state.update_data(roles=selected)
    await callback.message.edit_reply_markup(reply_markup=get_roles_keyboard(selected))
    await callback.answer()


@router.callback_query(TeamForm.roles, F.data == "roles:done")
async def team_roles_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected: list = data.get("roles", [])
    if not selected:
        await callback.answer("Выбери хотя бы одну роль.", show_alert=True)
        return
    team_name = data.get("team_name", "")
    description = data.get("description", "")
    pitch_format = data.get("pitch_format", "online")
    save_team(
        owner_id=callback.from_user.id,
        owner_username=callback.from_user.username,
        team_name=team_name or "",
        description=description,
        roles_needed=selected,
        pitch_format=pitch_format,
    )
    await state.clear()
    await callback.message.edit_text(
        "Команда зарегистрирована! Тебе будут приходить заявки от участников.",
        reply_markup=_team_menu_keyboard(callback.from_user.id, is_paused=False),
    )
    await callback.answer()


def _team_menu_keyboard(owner_id: int, is_paused: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        *get_team_dashboard_keyboard(owner_id, is_paused).inline_keyboard,
        [InlineKeyboardButton(text="В главное меню", callback_data="start")],
    ])


@router.callback_query(F.data == "team:requests")
async def team_requests(callback: CallbackQuery, state: FSMContext) -> None:
    owner_id = callback.from_user.id
    pending = get_pending_requests(owner_id)
    if not pending:
        await safe_edit_text(
            callback.message,
            "Нет новых заявок.",
            reply_markup=_team_menu_keyboard(owner_id, get_team(owner_id) and get_team(owner_id).get("is_paused", False)),
        )
        await callback.answer()
        return
    req = pending[0]
    solo = get_user(req["solo_id"])
    display_name = solo.get("display_name") or solo.get("username") or "—" if solo else "—"
    desc = solo.get("description", "—") if solo else "—"
    text = f"<b>Заявка</b> от {html.escape(display_name)}\n\n{html.escape(desc)}"
    await safe_edit_text(callback.message, text, reply_markup=get_request_keyboard(req["request_id"]))
    await callback.answer()


@router.callback_query(F.data == "team:search_solos")
async def team_search_solos(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_edit_text(
        callback.message,
        "Фильтр по специальности:",
        reply_markup=get_specialty_filter_keyboard(None),
    )
    await callback.answer()


def _team_back_to_search_keyboard(owner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← К поиску людей", callback_data="team:search_solos")],
        [InlineKeyboardButton(text="В меню команды", callback_data="mode:team")],
    ])


@router.callback_query(F.data.startswith("solofilter:"))
async def team_solofilter(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":", 2)
    filter_spec = parts[1] if len(parts) >= 2 else "all"
    active = get_active_users_by_specialty(filter_spec if filter_spec != "all" else None)
    total = len(active)
    if total == 0:
        await safe_edit_text(
            callback.message,
            "Нет активных анкет по выбранному фильтру.",
            reply_markup=_team_back_to_search_keyboard(callback.from_user.id),
        )
        await callback.answer()
        return
    page = 0
    key, solo = active[page]
    solo_id = solo["user_id"]
    display_name = solo.get("display_name") or solo.get("username") or "—"
    age = solo.get("age_category", "18+")
    fmt = solo.get("participation_format", "online")
    fmt_label = PARTICIPATION_FORMATS.get(fmt, fmt)
    spec = solo.get("specialty", "other")
    spec_label = SPECIALTIES.get(spec, spec)
    desc = solo.get("description", "")
    text = (
        f"<b>{html.escape(display_name)}</b> (страница {page + 1}/{total})\n"
        f"Возраст: {age} | Формат: {fmt_label} | Специальность: {spec_label}\n\n{html.escape(desc)}"
    )
    kb = get_solo_card_keyboard(solo_id, page, total, filter_spec)
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="← К фильтру", callback_data="team:search_solos"),
        InlineKeyboardButton(text="В меню", callback_data="mode:team"),
    ])
    await safe_edit_text(callback.message, text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("solobrowse:"))
async def team_solobrowse(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer()
        return
    filter_spec = parts[1]
    page = int(parts[2])
    active = get_active_users_by_specialty(filter_spec if filter_spec != "all" else None)
    total = len(active)
    if total == 0:
        await safe_edit_text(
            callback.message,
            "Нет активных анкет.",
            reply_markup=_team_back_to_search_keyboard(callback.from_user.id),
        )
        await callback.answer()
        return
    page = max(0, min(page, total - 1))
    key, solo = active[page]
    solo_id = solo["user_id"]
    display_name = solo.get("display_name") or solo.get("username") or "—"
    age = solo.get("age_category", "18+")
    fmt = solo.get("participation_format", "online")
    fmt_label = PARTICIPATION_FORMATS.get(fmt, fmt)
    spec = solo.get("specialty", "other")
    spec_label = SPECIALTIES.get(spec, spec)
    desc = solo.get("description", "")
    text = (
        f"<b>{html.escape(display_name)}</b> (страница {page + 1}/{total})\n"
        f"Возраст: {age} | Формат: {fmt_label} | Специальность: {spec_label}\n\n{html.escape(desc)}"
    )
    kb = get_solo_card_keyboard(solo_id, page, total, filter_spec)
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="← К фильтру", callback_data="team:search_solos"),
        InlineKeyboardButton(text="В меню", callback_data="mode:team"),
    ])
    await safe_edit_text(callback.message, text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("invite:"))
async def team_invite_solo(callback: CallbackQuery, state: FSMContext) -> None:
    solo_id = int(callback.data.split(":")[-1])
    owner_id = callback.from_user.id
    team = get_team(owner_id)
    if not team:
        await callback.answer("Команда не найдена.", show_alert=True)
        return
    invite_id = create_invite(owner_id, solo_id)
    if not invite_id:
        await callback.answer("Приглашение уже отправлено.", show_alert=True)
        return
    from keyboards import get_invite_keyboard
    team_name = team.get("team_name") or f"Команда #{team.get('team_number', '?')}"
    await callback.bot.send_message(
        solo_id,
        f"Команда «{html.escape(team_name)}» приглашает тебя!",
        reply_markup=get_invite_keyboard(invite_id),
    )
    await callback.answer("Приглашение отправлено.")
    await safe_edit_text(
        callback.message,
        "Приглашение отправлено. Ожидай ответа.",
        reply_markup=_team_back_to_search_keyboard(owner_id),
    )


@router.callback_query(F.data.startswith("accept:"))
async def accept_request(callback: CallbackQuery, state: FSMContext) -> None:
    request_id = callback.data.split(":")[-1]
    req = get_request(request_id)
    if not req or req["status"] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    team = get_team(callback.from_user.id)
    if not team or req["team_owner_id"] != callback.from_user.id:
        await callback.answer("Это не твоя заявка.", show_alert=True)
        return
    update_request_status(request_id, "accepted")
    solo = get_user(req["solo_id"])
    username = solo.get("username", "") if solo else ""
    if not username:
        username = f"пользователь (ID: {req['solo_id']})"
    else:
        username = f"@{username}"
    team_name = team.get("team_name") or f"Команда #{team.get('team_number', '?')}"
    await callback.bot.send_message(
        req["solo_id"],
        f"Поздравляю! Твою заявку приняла команда «{html.escape(team_name)}». Свяжутся с тобой.",
    )
    await safe_edit_text(callback.message, f"Заявка принята. Контакт: {username}")
    await callback.answer()


@router.callback_query(F.data.startswith("deny:"))
async def deny_request(callback: CallbackQuery, state: FSMContext) -> None:
    request_id = callback.data.split(":")[-1]
    req = get_request(request_id)
    if not req or req["status"] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    team = get_team(callback.from_user.id)
    if not team or req["team_owner_id"] != callback.from_user.id:
        await callback.answer("Это не твоя заявка.", show_alert=True)
        return
    update_request_status(request_id, "denied")
    await safe_edit_text(callback.message, "Заявка отклонена.")
    await callback.answer()


@router.callback_query(F.data == "team:toggle_pause")
async def team_toggle_pause(callback: CallbackQuery, state: FSMContext) -> None:
    owner_id = callback.from_user.id
    team = get_team(owner_id)
    if not team:
        await callback.answer("Сначала зарегистрируй команду.", show_alert=True)
        return
    is_paused = toggle_team_pause(owner_id)
    status = "закрыт" if is_paused else "возобновлён"
    await safe_edit_text(
        callback.message,
        f"Поиск {status}. " + ("Команда не показывается в поиске." if is_paused else "Команда снова видна участникам."),
        reply_markup=_team_menu_keyboard(owner_id, is_paused),
    )
    await callback.answer()


@router.callback_query(F.data == "team:delete_confirm")
async def team_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    from keyboards import get_confirm_delete_team_keyboard
    await safe_edit_text(
        callback.message,
        "Точно удалить анкету команды?",
        reply_markup=get_confirm_delete_team_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "team:delete_yes")
async def team_delete_yes(callback: CallbackQuery, state: FSMContext) -> None:
    owner_id = callback.from_user.id
    if not delete_team(owner_id):
        await callback.answer("Анкета не найдена.", show_alert=True)
        return
    await state.clear()
    from keyboards import get_mode_keyboard
    from handlers.start import GREETING
    await safe_edit_text(callback.message, GREETING, reply_markup=get_mode_keyboard())
    await callback.answer("Анкета команды удалена.")


@router.callback_query(F.data == "team:delete_no")
async def team_delete_no(callback: CallbackQuery, state: FSMContext) -> None:
    owner_id = callback.from_user.id
    team = get_team(owner_id)
    if not team:
        from keyboards import get_mode_keyboard
        from handlers.start import GREETING
        await safe_edit_text(callback.message, GREETING, reply_markup=get_mode_keyboard())
        await callback.answer()
        return
    is_paused = team.get("is_paused", False)
    team_name = team.get("team_name", "")
    team_number = team.get("team_number")
    display_name = team_name or (f"Команда #{team_number}" if team_number else "Команда")
    desc = team.get("description", "")
    roles_labels = [ROLES.get(r, r) for r in team.get("roles_needed", [])]
    roles_str = ", ".join(roles_labels) if roles_labels else "—"
    pitch = team.get("pitch_format", "online")
    pitch_str = "Онлайн" if pitch == "online" else "Офлайн"
    await safe_edit_text(
        callback.message,
        f"<b>{html.escape(display_name)}</b>\n\n{html.escape(desc)}\n\n<b>Ищете:</b> {roles_str}\n<b>Питчинг:</b> {pitch_str}\n\nСтатус: {'поиск закрыт' if is_paused else 'в поиске'}",
        reply_markup=_team_menu_keyboard(owner_id, is_paused),
    )
    await callback.answer()
