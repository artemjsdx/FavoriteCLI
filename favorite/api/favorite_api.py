import requests

from .base import IChatProvider, ChatMessage, ChatResponse


class FavoriteApiClient(IChatProvider):
  DEFAULT_BASE = "http://127.0.0.1:5005"

  def __init__(self, api_key: str, base_url: str = DEFAULT_BASE, model: str | None = None):
      self._key = api_key
      self._base = base_url.rstrip("/")
      self._model = model or "gemini-3.0-flash-thinking"
      self._headers = {
          "Authorization": f"Bearer {api_key}",
          "Content-Type": "application/json",
      }

  @property
  def provider_name(self) -> str:
      return "FavoriteAPI"

  def chat(self, messages: list[ChatMessage], model: str | None = None) -> ChatResponse:
      body: dict = {"messages": [{"role": m.role, "content": m.content} for m in messages]}
      if model or self._model:
          body["model"] = model or self._model
      r = requests.post(f"{self._base}/api/v1/chat", headers=self._headers, json=body, timeout=90)
      r.raise_for_status()
      data = r.json()
      content = data["choices"][0]["message"]["content"]
      ctx_kb = data.get("context_kb", 0.0)
      return ChatResponse(content=content, model=model or self._model, context_kb=ctx_kb, raw=data)

  def list_models(self) -> list[dict]:
      r = requests.get(f"{self._base}/api/v1/models", headers=self._headers, timeout=15)
      if r.status_code != 200:
          return []
      return r.json().get("models", [])

  def get_me(self) -> dict:
      r = requests.get(f"{self._base}/api/v1/me", headers=self._headers, timeout=15)
      if r.status_code == 200:
          return r.json()
      return {}

  @staticmethod
  def _parse_response(r) -> dict:
    """Разобрать ответ сервера: если HTML (Cloudflare/nginx ошибка) — вернуть понятное сообщение."""
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            pass
    text = (r.text or "").strip()
    if text.lower().startswith("<!doctype") or text.lower().startswith("<html"):
        return {"reset": False, "error": "Сервер FavoriteAPI недоступен (туннель Cloudflare не отвечает). Попробуй позже."}
    return {"reset": False, "error": text or f"HTTP {r.status_code}"}

  def reset_context(self) -> dict:
    """POST /api/v1/reset — сброс контекста. Возвращает dict с полем reset или requires_choice."""
    r = requests.post(f"{self._base}/api/v1/reset", headers=self._headers, timeout=15)
    return self._parse_response(r)

  def reset_context_apply(self, context: str = "clear", favorite: str = "keep") -> dict:
    """POST /api/v1/reset/apply — применить сброс с выбором что сохранить.
    context: 'clear' или 'keep'
    favorite: 'clear' или 'keep'
    """
    body = {"context": context, "favorite": favorite}
    r = requests.post(f"{self._base}/api/v1/reset/apply", headers=self._headers, json=body, timeout=15)
    return self._parse_response(r)
