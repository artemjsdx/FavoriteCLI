import requests
from .base import IChatProvider, ChatMessage, ChatResponse

BASE_URL = "https://integrate.api.nvidia.com/v1"

class NvidiaClient(IChatProvider):
  def __init__(self, api_key: str, model: str = "nvidia/llama-3.1-nemotron-70b-instruct"):
      self._key = api_key
      self._model = model
      self._headers = {
          "Authorization": f"Bearer {api_key}",
          "Content-Type": "application/json",
      }

  @property
  def provider_name(self) -> str:
      return "NVIDIA"

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
      return r.json().get("data", [])
