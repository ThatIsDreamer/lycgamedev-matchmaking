import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS: list[int] = []
_admin_raw = os.getenv("ADMIN_IDS", "")
if _admin_raw:
    ADMIN_IDS = [int(x.strip()) for x in _admin_raw.split(",") if x.strip()]
DATA_DIR = Path(__file__).resolve().parent / "data"
USERS_FILE = DATA_DIR / "users.json"
TEAMS_FILE = DATA_DIR / "teams.json"
REQUESTS_FILE = DATA_DIR / "requests.json"
INVITES_FILE = DATA_DIR / "invites.json"
