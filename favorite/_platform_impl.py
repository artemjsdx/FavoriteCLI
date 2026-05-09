import os
import subprocess
import sys
from abc import ABC, abstractmethod


class IPlatform(ABC):
  @abstractmethod
  def run_shell(self, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
      """Returns (returncode, stdout, stderr)."""

  @abstractmethod
  def run_shell_bg(self, name: str, cmd: str) -> bool:
      """Launch a background tmux session. Returns True on success."""

  @abstractmethod
  def read_tmux_log(self, name: str, lines: int = 50) -> str:
      """Read last N lines from a named tmux session."""

  @abstractmethod
  def notify(self, title: str, body: str) -> None:
      """Send a system notification."""

  @abstractmethod
  def vibrate(self, ms: int = 200) -> None:
      """Vibrate the device (Termux only)."""

  @property
  @abstractmethod
  def name(self) -> str:
      """Platform identifier."""


class TermuxPlatform(IPlatform):
  @property
  def name(self) -> str:
      return "termux"

  def run_shell(self, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
      try:
          result = subprocess.run(
              cmd, shell=True, capture_output=True, text=True, timeout=timeout
          )
          return result.returncode, result.stdout, result.stderr
      except subprocess.TimeoutExpired:
          return -1, "", f"Command timed out after {timeout}s"
      except Exception as e:
          return -1, "", str(e)

  def run_shell_bg(self, name: str, cmd: str) -> bool:
      rc, _, err = self.run_shell(
          f"tmux new-session -d -s {name} '{cmd}' 2>&1", timeout=5
      )
      return rc == 0

  def read_tmux_log(self, name: str, lines: int = 50) -> str:
      rc, out, _ = self.run_shell(
          f"tmux capture-pane -pt {name} -S -{lines} 2>&1"
      )
      return out if rc == 0 else ""

  def notify(self, title: str, body: str) -> None:
      self.run_shell(
          f'termux-notification --title "{title}" --content "{body}"', timeout=5
      )

  def vibrate(self, ms: int = 200) -> None:
      self.run_shell(f"termux-vibrate -d {ms}", timeout=3)


class LinuxFakePlatform(IPlatform):
  """Fake platform for development on Linux/Replit — logs instead of acting."""

  def __init__(self):
      self._log: list[str] = []

  @property
  def name(self) -> str:
      return "linux-fake"

  def _log_call(self, what: str) -> None:
      import datetime
      entry = f"[FAKE {datetime.datetime.now().strftime('%H:%M:%S')}] {what}"
      self._log.append(entry)
      print(f"\033[90m{entry}\033[0m", file=sys.stderr)

  def run_shell(self, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
      self._log_call(f"run_shell: {cmd!r} (timeout={timeout})")
      try:
          result = subprocess.run(
              cmd, shell=True, capture_output=True, text=True, timeout=timeout
          )
          return result.returncode, result.stdout, result.stderr
      except subprocess.TimeoutExpired:
          return -1, "", f"Timed out after {timeout}s"
      except Exception as e:
          return -1, "", str(e)

  def run_shell_bg(self, name: str, cmd: str) -> bool:
      self._log_call(f"run_shell_bg: name={name!r}, cmd={cmd!r}")
      return True

  def read_tmux_log(self, name: str, lines: int = 50) -> str:
      self._log_call(f"read_tmux_log: name={name!r}, lines={lines}")
      return f"[fake log output for session '{name}']"

  def notify(self, title: str, body: str) -> None:
      self._log_call(f"notify: title={title!r}, body={body!r}")

  def vibrate(self, ms: int = 200) -> None:
      self._log_call(f"vibrate: {ms}ms")

  def get_log(self) -> list[str]:
      return list(self._log)


def detect_platform() -> IPlatform:
  env_flag = os.environ.get("FAVORITE_PLATFORM", "").lower()
  if env_flag == "termux":
    return TermuxPlatform()
  if env_flag == "linux":
    return LinuxFakePlatform()
  prefix = os.environ.get("PREFIX", "")
  if "com.termux" in prefix:
    return TermuxPlatform()
  return LinuxFakePlatform()
