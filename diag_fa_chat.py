import sys, os, json, pathlib, requests
sys.path.insert(0, os.path.dirname(__file__))

cfg_path = pathlib.Path(__file__).parent / "config" / "api_keys.json"
cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
FA_KEY = os.environ.get("FA_API_KEY", cfg.get("favorite_api_key", ""))
FA_URL = os.environ.get("FA_BASE_URL", cfg.get("favorite_api_url", "http://127.0.0.1:5005"))
H = {"Authorization": f"Bearer {FA_KEY}", "Content-Type": "application/json"}

def test(label, payload):
    r = requests.post(f"{FA_URL}/api/v1/chat", json=payload, headers=H, timeout=30)
    print(f"Test {label}: status={r.status_code} body={r.text[:100]}")

# Test 1: no model (key default)
test("1-no-model", {"messages": [{"role": "user", "content": "ping"}]})
# Test 2: correct model
test("2-correct-model", {"messages": [{"role": "user", "content": "ping"}], "model": "gemini-3.0-flash-thinking"})
# Test 3: wrong model
test("3-wrong-model", {"messages": [{"role": "user", "content": "ping"}], "model": "gemini-2.0-flash-thinking-exp"})

from favorite.api.favorite_api import FavoriteApiClient
fa = FavoriteApiClient(FA_KEY, base_url=FA_URL)
mods = fa.list_models()
print("Models response:", {"models": [m.get("id") for m in mods[:5]]})
