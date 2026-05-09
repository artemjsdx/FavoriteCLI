import sys, os, json, pathlib
sys.path.insert(0, os.path.dirname(__file__))

cfg_path = pathlib.Path(__file__).parent / "config" / "api_keys.json"
cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
FA_KEY = os.environ.get("FA_API_KEY", cfg.get("favorite_api_key", ""))
FA_URL = os.environ.get("FA_BASE_URL", cfg.get("favorite_api_url", "http://127.0.0.1:5005"))
OR_KEY = os.environ.get("OR_API_KEY", cfg.get("openrouter_key", ""))

from favorite.api.favorite_api import FavoriteApiClient
from favorite.api.openrouter import OpenRouterClient
from favorite.api.base import ChatMessage
from favorite.agent.reincarnation_keeper import full_reincarnation_protocol

results = []

def p(name, ok, d=""):
    s = "PASS" if ok else "FAIL"
    results.append((s, name))
    print(f"[{s}] {name}" + (f" -> {str(d)[:100]}" if d else ""))

print("=== LIVE TEST v5 ===")

try:
    oc = OpenRouterClient(OR_KEY, model="qwen/qwen3.5-flash-02-23")
    r = oc.chat([ChatMessage(role="user", content="Reply only: OR_OK")])
    p("OpenRouter qwen3.5", True, r.content[:60])
except Exception as e:
    p("OpenRouter qwen3.5", False, str(e)[:80])

try:
    oc2 = OpenRouterClient(OR_KEY, model="qwen/qwen3-235b-a22b-2507")
    r2 = oc2.chat([ChatMessage(role="user", content="Reply only: OR_BIG_OK")])
    p("OpenRouter qwen3-235b", True, r2.content[:60])
except Exception as e:
    p("OpenRouter qwen3-235b", False, str(e)[:80])

try:
    fa = FavoriteApiClient(FA_KEY, base_url=FA_URL)
    me = fa.get_me()
    p("FA /me", True, f"model={me.get('default_model','?')}")
except Exception as e:
    p("FA /me", False, str(e)[:80])

try:
    fa2 = FavoriteApiClient(FA_KEY, base_url=FA_URL)
    rc = fa2.chat([ChatMessage(role="user", content="Reply only: FA_OK")])
    p("FA chat (no model)", True, rc.content[:60])
except Exception as e:
    p("FA chat (no model)", False, str(e)[:80])

try:
    fa3 = FavoriteApiClient(FA_KEY, base_url=FA_URL, model="gemini-3.0-flash-thinking")
    rc2 = fa3.chat([ChatMessage(role="user", content="Reply only: FA_MODEL_OK")])
    p("FA chat (gemini-3.0-flash-thinking)", True, rc2.content[:60])
except Exception as e:
    p("FA chat (gemini-3.0-flash-thinking)", False, str(e)[:80])

try:
    res = full_reincarnation_protocol("test-sess", "dying-agent-v5", "Session v5 complete", reset_callback=None)
    p("Reincarnation", True, f"keys={list(res.keys())}")
except Exception as e:
    p("Reincarnation", False, str(e)[:80])

passed = sum(1 for s,_ in results if s=="PASS")
print(f"\nITOG: {passed}/{len(results)} PASS")
