"""
favorite/ui/spinner.py
Animated gradient spinner with ellipsis "Thinking..." animation.
Dark-orange to light-orange gradient on both bullet and text.
"""
import threading
import time
import sys


# Dark orange gradient for bullet frames
_BULLET_COLORS = [
  "\033[38;2;180;60;0m",    # очень тёмный оранжевый
  "\033[38;2;210;90;0m",    # тёмный оранжевый
  "\033[38;2;255;140;0m",   # оранжевый (#ff8c00)
  "\033[38;2;230;110;0m",   # средний
]

# Gradient for label text: dark → orange
_LABEL_COLORS = [
  "\033[38;2;120;40;0m",    # тёмный коричневый
  "\033[38;2;160;60;0m",    # тёмный оранжевый
  "\033[38;2;200;90;0m",    # средний оранжевый
  "\033[38;2;255;140;0m",   # ярко-оранжевый
]

_BULLET_FRAMES = ["◐", "◓", "◑", "◒"]
_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"


class Spinner:
  """
  Animated spinner: bullet cycles ◐◓◑◒ with gradient.
  Label text also cycles with gradient + ellipsis animation: "Thinking", "Thinking.", "Thinking..", "Thinking..."
  
  All on one line via carriage return. Slow animation (0.3s per frame).
  """

  def __init__(self, label: str = ""):
      self.label = label
      self._stop_event = threading.Event()
      self._thread: threading.Thread | None = None

  def start(self) -> None:
      self._stop_event.clear()
      self._thread = threading.Thread(target=self._spin, daemon=True)
      self._thread.start()

  def stop(self) -> None:
      self._stop_event.set()
      if self._thread:
          self._thread.join(timeout=0.5)
      # Clear the spinner line
      sys.stdout.write("\r\033[K")
      sys.stdout.flush()

  def _spin(self) -> None:
      import time as _time
      _start = _time.time()
      i = 0
      while not self._stop_event.is_set():
          bullet_idx = i % len(_BULLET_FRAMES)
          bullet_frame = _BULLET_FRAMES[bullet_idx]
          bullet_color = _BULLET_COLORS[bullet_idx % len(_BULLET_COLORS)]

          label_idx = (i // 4) % len(_LABEL_COLORS)
          label_color = _LABEL_COLORS[label_idx]

          dots_count = i % 4
          dots = "." * dots_count
          label_text = self.label + dots if self.label else ""

          elapsed = int(_time.time() - _start)
          time_part = f" \033[2m\033[38;2;80;80;80m{elapsed}s{_RESET}" if elapsed >= 1 else ""

          line = (
              f"\r  {_BOLD}{bullet_color}{bullet_frame}{_RESET} "
              f"{_BOLD}{label_color}{label_text}{_RESET}{time_part}   "
          )
          sys.stdout.write(line)
          sys.stdout.flush()

          i += 1
          self._stop_event.wait(0.3)
