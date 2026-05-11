"""
  favorite/skills/device_ctrl/adb_client.py — ADB-транспорт.
  Обёртка над subprocess для adb -s ip:port ...
  """
  import subprocess
  import base64
  import tempfile
  import time
  from pathlib import Path
  from . import config as dcfg


  class AdbError(Exception):
      pass


  class AdbClient:
      def __init__(self, serial: str, timeout: int = 15):
          self.serial = serial
          self.timeout = timeout

      def _run(self, *args, timeout: int | None = None, input_data: str | None = None) -> str:
          cmd = ["adb", "-s", self.serial, *args]
          try:
              r = subprocess.run(
                  cmd,
                  capture_output=True,
                  text=True,
                  timeout=timeout or self.timeout,
                  input=input_data,
              )
              if r.returncode != 0 and r.stderr:
                  raise AdbError(r.stderr.strip())
              return (r.stdout or "").strip()
          except subprocess.TimeoutExpired:
              raise AdbError(f"ADB timeout ({timeout or self.timeout}s): {' '.join(args)}")
          except FileNotFoundError:
              raise AdbError("adb не найден. Установи: pkg install android-tools")

      # ── Соединение ──────────────────────────────────────────────────────────
      @classmethod
      def connect(cls, ip: str, port: int = 5555, timeout: int = 15) -> "AdbClient":
          serial = f"{ip}:{port}"
          try:
              r = subprocess.run(
                  ["adb", "connect", serial],
                  capture_output=True, text=True, timeout=timeout
              )
              out = (r.stdout or "").lower()
              if "connected" in out or "already connected" in out:
                  return cls(serial, timeout)
              raise AdbError(f"Не удалось подключиться: {r.stdout.strip()}")
          except FileNotFoundError:
              raise AdbError("adb не найден. Установи: pkg install android-tools")

      @classmethod
      def connect_by_pair(cls, ip: str, pair_port: int, code: str, main_port: int = 5555) -> "AdbClient":
          subprocess.run(["adb", "pair", f"{ip}:{pair_port}", code], capture_output=True, timeout=30)
          return cls.connect(ip, main_port)

      def disconnect(self) -> None:
          subprocess.run(["adb", "disconnect", self.serial], capture_output=True, timeout=10)

      def check_connected(self) -> bool:
          try:
              r = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
              return self.serial in r.stdout
          except Exception:
              return False

      # ── Device info ─────────────────────────────────────────────────────────
      def device_info(self) -> dict:
          def prop(key):
              try:
                  return self._run("shell", f"getprop {key}", timeout=5)
              except Exception:
                  return "?"
          model = prop("ro.product.model")
          brand = prop("ro.product.brand")
          android = prop("ro.build.version.release")
          sdk = prop("ro.build.version.sdk")
          # Screen resolution
          try:
              wm = self._run("shell", "wm size", timeout=5)
              res = wm.split(":")[-1].strip() if ":" in wm else "?"
          except Exception:
              res = "?"
          return {
              "serial": self.serial,
              "model": f"{brand} {model}".strip(),
              "android": f"Android {android} (SDK {sdk})",
              "resolution": res,
          }

      # ── Скриншот ─────────────────────────────────────────────────────────────
      def screenshot_b64(self) -> str:
          remote = "/sdcard/.fav_screen.png"
          self._run("shell", f"screencap -p {remote}")
          tmp = tempfile.mktemp(suffix=".png")
          try:
              subprocess.run(["adb", "-s", self.serial, "pull", remote, tmp],
                             capture_output=True, timeout=15, check=True)
              self._run("shell", f"rm -f {remote}")
              data = Path(tmp).read_bytes()
              return base64.b64encode(data).decode()
          finally:
              Path(tmp).unlink(missing_ok=True)

      def screenshot_bytes(self) -> bytes:
          return base64.b64decode(self.screenshot_b64())

      # ── UI dump ──────────────────────────────────────────────────────────────
      def ui_dump(self) -> str:
          remote = "/sdcard/.fav_ui_dump.xml"
          self._run("shell", f"uiautomator dump {remote}")
          tmp = tempfile.mktemp(suffix=".xml")
          try:
              subprocess.run(["adb", "-s", self.serial, "pull", remote, tmp],
                             capture_output=True, timeout=15, check=True)
              self._run("shell", f"rm -f {remote}")
              return Path(tmp).read_text(encoding="utf-8", errors="replace")
          finally:
              Path(tmp).unlink(missing_ok=True)

      # ── Действия ─────────────────────────────────────────────────────────────
      def tap(self, x: int, y: int) -> None:
          self._run("shell", f"input tap {x} {y}")
          delay = dcfg.load().get("action_delay_ms", 500)
          time.sleep(delay / 1000)

      def type_text(self, text: str) -> None:
          escaped = text.replace(" ", "%s").replace("'", "\'")
          self._run("shell", f"input text '{escaped}'")

      def swipe(self, x1: int, y1: int, x2: int, y2: int, ms: int = 300) -> None:
          self._run("shell", f"input swipe {x1} {y1} {x2} {y2} {ms}")

      def press_key(self, key: str) -> None:
          key_map = {
              "back": "4", "home": "3", "enter": "66",
              "recent": "187", "menu": "82", "power": "26",
              "volume_up": "24", "volume_down": "25", "del": "67",
          }
          code = key_map.get(key.lower(), key)
          self._run("shell", f"input keyevent {code}")

      def launch_app(self, pkg: str) -> None:
          self._run("shell", f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")

      def list_apps(self, include_system: bool = False) -> list[str]:
          flag = "" if include_system else "-3"
          out = self._run("shell", f"pm list packages {flag}")
          pkgs = []
          for line in out.splitlines():
              if line.startswith("package:"):
                  pkgs.append(line[8:].strip())
          return sorted(pkgs)

      def clear_field(self) -> None:
          # Select all + delete
          self._run("shell", "input keyevent 29")   # ctrl+A (KEYCODE_A) – no, let's do long press
          self._run("shell", "input keyevent --longpress 67")
  