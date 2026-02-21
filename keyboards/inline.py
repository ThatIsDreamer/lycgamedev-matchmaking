from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

ROLES = {
    "designer": "Дизайнер",
    "programmer": "Программист",
    "music": "Музыка",
    "other": "Другое",
}

SPECIALTIES = {
    "gamedesign": "Геймдизайн",
    "designer": "Дизайнер",
    "programmer": "Программист",
    "artist": "Художник",
    "sound": "Звук/музыка",
    "producer": "Продюсер",
    "other": "Другое",
}

AGE_CATEGORIES = {
    "18-": "18-",
    "18+": "18+",
}

PARTICIPATION_FORMATS = {
    "online": "Онлайн",
    "offline": "Офлайн",
}

MAX_CALLBACK_DATA_LEN = 64


def get_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ищу команду", callback_data="mode:solo")],
        [InlineKeyboardButton(text="Мы команда, ищем людей", callback_data="mode:team")],
    ])


def get_roles_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for role_id, label in ROLES.items():
        prefix = "✓ " if role_id in selected else ""
        rows.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"role:{role_id}")])
    rows.append([InlineKeyboardButton(text="Готово", callback_data="roles:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_team_card_keyboard(team_owner_id: int, page: int, total: int) -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(text="Отправить заявку", callback_data=f"request:{team_owner_id}")]
    row2 = []
    if page > 0:
        row2.append(InlineKeyboardButton(text="← Назад", callback_data=f"browse:{page - 1}"))
    if page < total - 1:
        row2.append(InlineKeyboardButton(text="Вперёд →", callback_data=f"browse:{page + 1}"))
    kb = [row1]
    if row2:
        kb.append(row2)
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_request_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Принять", callback_data=f"accept:{request_id}"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"deny:{request_id}"),
        ],
    ])


def get_team_dashboard_keyboard(owner_id: int, is_paused: bool) -> InlineKeyboardMarkup:
    pause_text = "Возобновить поиск" if is_paused else "Закрыть поиск"  # when not paused, show "Закрыть"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Новые заявки", callback_data="team:requests")],
        [InlineKeyboardButton(text="Искать людей", callback_data="team:search_solos")],
        [InlineKeyboardButton(text=pause_text, callback_data="team:toggle_pause")],
        [InlineKeyboardButton(text="Удалить анкету команды", callback_data="team:delete_confirm")],
    ])


def get_age_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="18-", callback_data="age:18-")],
        [InlineKeyboardButton(text="18+", callback_data="age:18+")],
    ])


def get_participation_format_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Онлайн", callback_data="format:online")],
        [InlineKeyboardButton(text="Офлайн", callback_data="format:offline")],
    ])


def get_specialty_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=f"specialty:{sid}")] for sid, label in SPECIALTIES.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_pitch_format_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Онлайн", callback_data="pitch:online")],
        [InlineKeyboardButton(text="Офлайн", callback_data="pitch:offline")],
    ])


def get_team_name_skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без названия", callback_data="team_name:skip")],
    ])


def get_solo_card_keyboard(solo_id: int, page: int, total: int, filter_spec: str = "all") -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(text="Пригласить в команду", callback_data=f"invite:{solo_id}")]
    row2 = []
    if page > 0:
        row2.append(InlineKeyboardButton(text="← Назад", callback_data=f"solobrowse:{filter_spec}:{page - 1}"))
    if page < total - 1:
        row2.append(InlineKeyboardButton(text="Вперёд →", callback_data=f"solobrowse:{filter_spec}:{page + 1}"))
    kb = [row1]
    if row2:
        kb.append(row2)
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_specialty_filter_keyboard(current_specialty: str | None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Все специальности", callback_data="solofilter:all")]]
    for sid, label in SPECIALTIES.items():
        prefix = "✓ " if current_specialty == sid else ""
        rows.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"solofilter:{sid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_invite_keyboard(invite_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Принять", callback_data=f"invite_accept:{invite_id}"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"invite_deny:{invite_id}"),
        ],
    ])


def get_confirm_delete_team_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, удалить", callback_data="team:delete_yes"),
            InlineKeyboardButton(text="Нет", callback_data="team:delete_no"),
        ],
    ])


