"""
favorite/skills/telegram_notify.py
Telegram notification system for FavoriteCLI.
Pure urllib — no external TG libraries required.
All sends fire-and-forget in background thread.
"""
import json
import threading
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Optional


class TelegramNotifier:
  def __init__(self, config_path: str | Path = "config/telegram.json"):
      self._cfg_path = Path(config_path)
      self._cfg = self._load_config()
      self._log_path: Optional[Path] = None

  def _load_config(self) -> dict:
      try:
          if self._cfg_path.exists():
              return json.loads(self._cfg_path.read_text(encoding="utf-8"))
      except Exception:
          pass
      return {
          "bot_token": "", "recipients": [], "enabled": False,
          "routing": "log_only", "quiet_hours": None,
          "events": {
              "final_answers": True, "main_thoughts": True,
              "sub_replies": False, "system_events": True,
              "votes": True, "checkpoints": True, "steps": False, "questions": True
          }
      }

  def reload_config(self) -> None:
      self._cfg = self._load_config()

  def save_config(self) -> None:
      try:
          self._cfg_path.parent.mkdir(parents=True, exist_ok=True)
          self._cfg_path.write_text(
              json.dumps(self._cfg, ensure_ascii=False, indent=2), encoding="utf-8"
          )
      except Exception:
          pass

  def set_session_dir(self, sess_dir: Path) -> None:
      self._log_path = sess_dir / "telegram.log"

  @property
  def enabled(self) -> bool:
      return bool(
          self._cfg.get("enabled")
          and self._cfg.get("bot_token")
          and self._cfg.get("recipients")
      )

  def _is_quiet_hour(self) -> bool:
      qh = self._cfg.get("quiet_hours")
      if not qh:
          return False
      try:
          now_h = datetime.now().hour
          start, end = int(qh["start"]), int(qh["end"])
          if start <= end:
              return start <= now_h < end
          return now_h >= start or now_h < end
      except Exception:
          return False

  def _log(self, event_type: str, text: str) -> None:
      if not self._log_path:
          return
      try:
          ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          line = json.dumps(
              {"ts": ts, "type": event_type, "text": text[:500]},
              ensure_ascii=False
          )
          self._log_path.parent.mkdir(parents=True, exist_ok=True)
          with open(self._log_path, "a", encoding="utf-8") as f:
              f.write(line + "\n")
      except Exception:
          pass

  def _send_bg(self, text: str, mandatory: bool = False) -> None:
      """Fire-and-forget send to all recipients."""
      if not self.enabled:
          return
      if self._is_quiet_hour() and not mandatory:
          return
      routing = self._cfg.get("routing", "log_only")
      if routing == "log_only":
          return
      token = self._cfg.get("bot_token", "")
      recipients = list(self._cfg.get("recipients", []))

      def _do_send() -> None:
          url = f"https://api.telegram.org/bot{token}/sendMessage"
          for recipient in recipients:
              try:
                  body = json.dumps({
                      "chat_id": recipient,
                      "text": text[:4000],
                      "parse_mode": "HTML"
                  }).encode("utf-8")
                  req = urllib.request.Request(
                      url, data=body,
                      headers={"Content-Type": "application/json"},
                      method="POST"
                  )
                  urllib.request.urlopen(req, timeout=10)
              except Exception:
                  pass

      threading.Thread(target=_do_send, daemon=True).start()

  def _event_enabled(self, key: str) -> bool:
      return bool(self._cfg.get("events", {}).get(key, False))

  # ─── Public notify methods ─────────────────────────────────────────────────

  def notify_final_answer(self, agent_name: str, text: str) -> None:
      self._log("final_answer", f"[{agent_name}] {text}")
      if not self._event_enabled("final_answers"):
          return
      tg = f"<b>● {self._esc(agent_name)}</b>\n{self._esc(text[:1000])}"
      self._send_bg(tg, mandatory=True)

  def notify_step(self, text: str) -> None:
      self._log("step", text)
      if not self._event_enabled("steps"):
          return
      self._send_bg(f"<i>Step: {self._esc(text[:500])}</i>")

  def notify_sub_reply(self, from_agent: str, text: str) -> None:
      self._log("sub_reply", f"[{from_agent}] {text}")
      if not self._event_enabled("sub_replies"):
          return
      self._send_bg(f"<b>[SUB] {self._esc(from_agent)}</b>\n{self._esc(text[:500])}")

  def notify_checkpoint(self, note: str) -> None:
      self._log("checkpoint", note)
      if not self._event_enabled("checkpoints"):
          return
      self._send_bg(f"[CHECKPOINT] {self._esc(note)}")

  def notify_system_event(self, event_type: str, text: str) -> None:
      self._log("system_event", f"[{event_type}] {text}")
      if not self._event_enabled("system_events"):
          return
      self._send_bg(f"[{self._esc(event_type)}] {self._esc(text[:500])}")

  def notify_question(self, text: str) -> None:
      self._log("question", text)
      tg = f"[QUESTION] {self._esc(text[:500])}"
      self._send_bg(tg, mandatory=True)

  def test_connection(self) -> bool:
      """Send a test message. Returns True on success."""
      token = self._cfg.get("bot_token", "")
      recipients = self._cfg.get("recipients", [])
      if not token or not recipients:
          return False
      url = f"https://api.telegram.org/bot{token}/sendMessage"
      for recipient in recipients:
          try:
              body = json.dumps({
                  "chat_id": recipient,
                  "text": "FavoriteCLI connected successfully.",
                  "parse_mode": "HTML"
              }).encode("utf-8")
              req = urllib.request.Request(
                  url, data=body,
                  headers={"Content-Type": "application/json"},
                  method="POST"
              )
              urllib.request.urlopen(req, timeout=10)
              return True
          except Exception:
              return False
      return False

  @staticmethod
  def _esc(text: str) -> str:
      return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
