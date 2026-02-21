from aiogram import F, Router
from aiogram.types import Message

from config import ADMIN_IDS
from storage import get_active_teams, get_requests, get_teams, get_users

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(F.text.in_(["/admin", "/stats"]))
async def cmd_admin_stats(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return
    teams = get_teams()
    active_teams = get_active_teams()
    users = get_users()
    active_users = [u for u in users.values() if u.get("is_active", True)]
    requests = get_requests()
    pending_requests = [r for r in requests.values() if r.get("status") == "pending"]
    text = (
        "<b>Статистика</b>\n\n"
        f"Всего команд: {len(teams)}\n"
        f"Команд в поиске: {len(active_teams)}\n"
        f"Всего личных анкет: {len(users)}\n"
        f"Активных анкет: {len(active_users)}\n"
        f"Заявок в ожидании: {len(pending_requests)}"
    )
    await message.answer(text)
