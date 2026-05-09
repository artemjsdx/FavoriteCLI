import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from favorite.api.favorite_api import FavoriteApiClient
from favorite.api.openrouter import OpenRouterClient
from favorite.api.base import ChatMessage
import json, pathlib

cfg_path = pathlib.Path(__file__).parent / "config" / "api_keys.json"
cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
FA_KEY = os.environ.get("FA_API_KEY", cfg.get("favorite_api_key", ""))
FA_URL = os.environ.get("FA_BASE_URL", cfg.get("favorite_api_url", "http://127.0.0.1:5005"))
OR_KEY = os.environ.get("OR_API_KEY", cfg.get("openrouter_key", ""))
results = []

def p(name, ok, d=""):
    s = "PASS" if ok else "FAIL"
    results.append((s, name))
    print(f"  [{s}] {name}" + (f"\n    -> {str(d)[:100]}" if d else ""))

print("=== VERIFY ALL APIS ===")

try:
    fa = FavoriteApiClient(FA_KEY, base_url=FA_URL)
    r = fa.chat([ChatMessage(role="user", content="Reply only: FA_NO_MODEL_OK")])
    p("FA chat (no model)", True, r.content[:80])
except Exception as e:
    p("FA chat (no model)", False, str(e)[:80])

try:
    fa2 = FavoriteApiClient(FA_KEY, base_url=FA_URL, model="gemini-3.0-flash-thinking")
    r2 = fa2.chat([ChatMessage(role="user", content="Reply only: FA_CORRECT_MODEL_OK")])
    p("FA chat (gemini-3.0-flash-thinking)", True, r2.content[:80])
except Exception as e:
    p("FA chat (gemini-3.0-flash-thinking)", False, str(e)[:80])

try:
    oc = OpenRouterClient(OR_KEY, model="qwen/qwen3.5-flash-02-23")
    r3 = oc.chat([ChatMessage(role="user", content="Reply only: OR_QWEN35_OK")])
    p("OR qwen3.5-flash-02-23", True, r3.content[:80])
except Exception as e:
    p("OR qwen3.5-flash-02-23", False, str(e)[:80])

try:
    fa3 = FavoriteApiClient(FA_KEY, base_url=FA_URL)
    mods = fa3.list_models()
    p("FA list_models()", len(mods) > 0, f"{len(mods)} models")
except Exception as e:
    p("FA list_models()", False, str(e)[:80])

try:
    from favorite.agent.reincarnation_keeper import full_reincarnation_protocol
    res = full_reincarnation_protocol("verify-sess", "dying-v5", "Final verify brief")
    p("full_reincarnation_protocol()", True, f"keys={list(res.keys())}")
except Exception as e:
    p("full_reincarnation_protocol()", False, str(e)[:80])

passed = sum(1 for s,_ in results if s=="PASS")
print(f"\n=== ИТОГ: {passed}/{len(results)} PASS ===")
