import requests

from .base import IChatProvider, ChatMessage, ChatResponse

BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient(IChatProvider):
  def __init__(self, api_key: str, model: str = "qwen/qwen3-coder:free"):
      self._key = api_key
      self._model = model
      self._headers = {
          "Authorization": f"Bearer {api_key}",
          "Content-Type": "application/json",
          "HTTP-Referer": "https://github.com/animebyst07-stack/FavoriteCLI",
          "X-Title": "FavoriteCLI",
      }

  @property
  def provider_name(self) -> str:
      return "OpenRouter"

  def chat(self, messages: list[ChatMessage], model: str | None = None) -> ChatResponse:
      body = {
          "model": model or self._model,
          "messages": [{"role": m.role, "content": m.content} for m in messages],
      }
      r = requests.post(
          f"{BASE_URL}/chat/completions",
          headers=self._headers,
          json=body,
          timeout=60,
      )
      r.raise_for_status()
      data = r.json()
      if "error" in data:
          raise RuntimeError(data["error"].get("message", str(data["error"])))
      content = data["choices"][0]["message"]["content"]
      return ChatResponse(content=content, model=model or self._model, raw=data)

  def list_models(self) -> list[dict]:
      r = requests.get(f"{BASE_URL}/models", headers=self._headers, timeout=20)
      if r.status_code != 200:
          return []
      models = r.json().get("data", [])
      def sort_key(m):
          p = m.get("pricing", {})
          try:
              return float(p.get("prompt", 0)) + float(p.get("completion", 0))
          except (TypeError, ValueError):
              return float("inf")
      models.sort(key=sort_key)
      return models
