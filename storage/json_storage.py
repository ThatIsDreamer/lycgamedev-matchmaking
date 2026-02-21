import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from config import INVITES_FILE, REQUESTS_FILE, TEAMS_FILE, USERS_FILE


def _ensure_file(path: Path, default: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")


def _read(path: Path) -> dict:
    _ensure_file(path, {})
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".json")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        Path(tmp).replace(path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


# --- Users ---
def get_users() -> dict[str, dict]:
    return _read(USERS_FILE)


def get_user(user_id: int) -> dict | None:
    users = get_users()
    return users.get(str(user_id))


def save_user(
    user_id: int,
    username: str | None,
    display_name: str,
    age_category: str,
    participation_format: str,
    specialty: str,
    description: str,
    is_active: bool = True,
) -> None:
    users = get_users()
    existing = users.get(str(user_id), {})
    users[str(user_id)] = {
        "user_id": user_id,
        "username": username or "",
        "display_name": display_name or (username or ""),
        "age_category": age_category,
        "participation_format": participation_format,
        "specialty": specialty,
        "description": description,
        "is_active": existing.get("is_active", True) if existing else True,
        "created_at": existing.get("created_at", datetime.utcnow().isoformat()),
    }
    _write(USERS_FILE, users)


def set_user_active(user_id: int, is_active: bool) -> bool:
    users = get_users()
    key = str(user_id)
    if key not in users:
        return False
    users[key]["is_active"] = is_active
    _write(USERS_FILE, users)
    return True


def get_active_users() -> list[tuple[str, dict]]:
    users = get_users()
    return [(k, v) for k, v in users.items() if v.get("is_active", True)]


def get_active_users_by_specialty(specialty: str | None) -> list[tuple[str, dict]]:
    active = get_active_users()
    if not specialty or specialty == "all":
        return active
    return [(k, v) for k, v in active if v.get("specialty", "other") == specialty]


# --- Teams ---
def get_teams() -> dict[str, dict]:
    return _read(TEAMS_FILE)


def get_team(owner_id: int) -> dict | None:
    teams = get_teams()
    return teams.get(f"owner_{owner_id}")


def get_active_teams() -> list[tuple[str, dict]]:
    """Returns list of (team_key, team) for teams where is_paused is False."""
    teams = get_teams()
    return [(k, v) for k, v in teams.items() if not v.get("is_paused", False)]


def _next_team_number() -> int:
    teams = get_teams()
    numbers = [t.get("team_number") for t in teams.values() if isinstance(t.get("team_number"), int)]
    return max(numbers, default=0) + 1


def save_team(
    owner_id: int,
    owner_username: str | None,
    team_name: str,
    description: str,
    roles_needed: list[str],
    pitch_format: str = "online",
) -> None:
    teams = get_teams()
    key = f"owner_{owner_id}"
    existing = teams.get(key, {})
    team_number = existing.get("team_number")
    if team_number is None:
        team_number = _next_team_number()
    teams[key] = {
        "owner_id": owner_id,
        "owner_username": owner_username or "",
        "team_number": team_number,
        "team_name": team_name or "",
        "description": description,
        "roles_needed": roles_needed,
        "pitch_format": pitch_format,
        "is_paused": existing.get("is_paused", False),
        "members": existing.get("members", []),
        "created_at": existing.get("created_at", datetime.utcnow().isoformat()),
    }
    _write(TEAMS_FILE, teams)


def delete_team(owner_id: int) -> bool:
    teams = get_teams()
    key = f"owner_{owner_id}"
    if key not in teams:
        return False
    del teams[key]
    _write(TEAMS_FILE, teams)
    return True


def toggle_team_pause(owner_id: int) -> bool:
    """Toggles is_paused for the team. Returns new is_paused value."""
    teams = get_teams()
    key = f"owner_{owner_id}"
    if key not in teams:
        return False
    teams[key]["is_paused"] = not teams[key].get("is_paused", False)
    _write(TEAMS_FILE, teams)
    return teams[key]["is_paused"]


# --- Requests ---
def get_requests() -> dict[str, dict]:
    return _read(REQUESTS_FILE)


def create_request(solo_id: int, team_owner_id: int) -> str | None:
    """Creates a pending request. Returns request_id or None if duplicate."""
    requests = get_requests()
    for req in requests.values():
        if req["solo_id"] == solo_id and req["team_owner_id"] == team_owner_id and req["status"] == "pending":
            return None
    ts = int(datetime.utcnow().timestamp())
    request_id = f"{solo_id}_{team_owner_id}_{ts}"
    requests[request_id] = {
        "request_id": request_id,
        "solo_id": solo_id,
        "team_owner_id": team_owner_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    _write(REQUESTS_FILE, requests)
    return request_id


def get_request(request_id: str) -> dict | None:
    return get_requests().get(request_id)


def get_request_by_solo_and_team(solo_id: int, team_owner_id: int) -> dict | None:
    for req in get_requests().values():
        if req["solo_id"] == solo_id and req["team_owner_id"] == team_owner_id:
            return req
    return None


def get_pending_requests(team_owner_id: int) -> list[dict]:
    return [r for r in get_requests().values() if r["team_owner_id"] == team_owner_id and r["status"] == "pending"]


def update_request_status(request_id: str, status: str) -> bool:
    requests = get_requests()
    if request_id not in requests:
        return False
    requests[request_id]["status"] = status
    _write(REQUESTS_FILE, requests)
    return True


# --- Invites (team -> solo) ---
def get_invites() -> dict[str, dict]:
    return _read(INVITES_FILE)


def create_invite(team_owner_id: int, solo_id: int) -> str | None:
    invites = get_invites()
    for inv in invites.values():
        if inv["team_owner_id"] == team_owner_id and inv["solo_id"] == solo_id and inv.get("status") == "pending":
            return None
    ts = int(datetime.utcnow().timestamp())
    invite_id = f"inv_{team_owner_id}_{solo_id}_{ts}"
    invites[invite_id] = {
        "invite_id": invite_id,
        "team_owner_id": team_owner_id,
        "solo_id": solo_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    _write(INVITES_FILE, invites)
    return invite_id


def get_invite(invite_id: str) -> dict | None:
    return get_invites().get(invite_id)


def get_pending_invites_for_solo(solo_id: int) -> list[dict]:
    return [i for i in get_invites().values() if i["solo_id"] == solo_id and i.get("status") == "pending"]


def update_invite_status(invite_id: str, status: str) -> bool:
    invites = get_invites()
    if invite_id not in invites:
        return False
    invites[invite_id]["status"] = status
    _write(INVITES_FILE, invites)
    return True
