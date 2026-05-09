import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from favorite.bridge.tg_url import fetch_url
import json, pathlib

# Credentials loaded from config (not hardcoded)
cfg_path = pathlib.Path(__file__).parent / "config" / "api_keys.json"
cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", cfg.get("tg_bot_token", ""))
CHAT_ID = os.environ.get("TG_CHAT_ID", cfg.get("tg_chat_id", ""))

url = fetch_url(BOT_TOKEN, CHAT_ID)
print("FA URL:", url)
