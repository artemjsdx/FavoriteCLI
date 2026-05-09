"""
FavoriteCLI — bridge/tg_url.py
Читает актуальный URL FavoriteAPI из pinned_message в Telegram-чате.
FavoriteAPI пинит своё красивое уведомление; URL хранится в entities (text_link).
"""
import json
import time
import urllib.request
import urllib.error
from typing import Optional

_cache: dict = {"url": None, "ts": 0.0}
_TTL = 30.0  # секунд


def fetch_url(bot_token: str, chat_id: str) -> Optional[str]:
  """Возвращает URL из pinned_message.entities. Кеш 30 сек."""
  now = time.time()
  if _cache["url"] and now - _cache["ts"] < _TTL:
      return _cache["url"]
  url = _fetch_from_pinned(bot_token, chat_id)
  if url:
      _cache["url"] = url
      _cache["ts"] = now
  return url


def invalidate() -> None:
  """Сбросить кеш (вызывать перед повторным фетчем после ConnectionError)."""
  _cache["url"] = None
  _cache["ts"] = 0.0


def _tg_request(bot_token: str, method: str, payload: dict) -> Optional[dict]:
  """Отправить запрос к Telegram Bot API. Возвращает result или None."""
  try:
      data = json.dumps(payload).encode("utf-8")
      req = urllib.request.Request(
          f"https://api.telegram.org/bot{bot_token}/{method}",
          data=data,
          headers={"Content-Type": "application/json"},
          method="POST",
      )
      with urllib.request.urlopen(req, timeout=10) as resp:
          parsed = json.loads(resp.read().decode("utf-8"))
      if parsed.get("ok"):
          return parsed["result"]
  except Exception:
      pass
  return None


def _get_pinned(bot_token: str, chat_id) -> Optional[dict]:
  """getChat для указанного chat_id. Возвращает pinned_message или None."""
  result = _tg_request(bot_token, "getChat", {"chat_id": chat_id})
  if result:
      return result.get("pinned_message")
  return None


def _url_from_message(msg: dict) -> Optional[str]:
  """Извлечь URL из entities сообщения (text_link или plain FAPI_URL:)."""
  for entity in msg.get("entities", []):
      if entity.get("type") == "text_link":
          url = entity.get("url", "")
          if url.startswith("http"):
              return url
  text = msg.get("text", "")
  if "FAPI_URL:" in text:
      for part in text.split():
          if part.startswith("FAPI_URL:"):
              return part[len("FAPI_URL:"):]
  for word in text.split():
      if "trycloudflare.com" in word:
          return word.strip(".,()[]<>")
  return None


def _fetch_from_pinned(bot_token: str, raw_chat_id: str) -> Optional[str]:
  """Пробует оба варианта chat_id (raw и с префиксом -100 для каналов)."""
  for cid in _resolve_candidates(raw_chat_id):
      pinned = _get_pinned(bot_token, cid)
      if pinned:
          url = _url_from_message(pinned)
          if url:
              return url
  return None


def _resolve_candidates(raw: str) -> list:
  """
  Для положительных чисел пробуем -100<num> (канал/супергруппа) и raw.
  """
  raw = str(raw).strip()
  if raw.startswith("@"):
      return [raw]
  if raw.startswith("-"):
      try:
          return [int(raw)]
      except ValueError:
          return [raw]
  try:
      num = int(raw)
      if num > 0:
          return [int(f"-100{num}"), num]
      return [num]
  except ValueError:
      return [raw]
