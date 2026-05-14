"""
favorite/ui/chat.py
Claude Code-style terminal UI.
"""
import re
import threading
from rich.console import Console
from rich.markup import escape
from rich.text import Text
from .theme import ORANGE, WHITE, GRAY, DIM

console = Console()

# ─── Code-block renderer (без цветного фона) ──────────────────────────────────

_CODE_FENCE = re.compile(r'```(?:[\w+-]*)\n?(.*?)```', re.DOTALL)
_INLINE_CODE = re.compile(r'`([^`\n]+)`')
_INLINE_MD   = re.compile(
  r'(\*\*\*(.+?)\*\*\*'   # bold+italic
  r'|\*\*(.+?)\*\*'          # bold
  r'|\*(.+?)\*'                # italic
  r'|`([^`\n]+)`)'           # inline code
)


def _apply_inline(text: str) -> str:
  """Конвертирует **bold**, *italic*, `code` в Rich-разметку. Всё остальное экранируется."""
  result = ""
  last = 0
  for m in _INLINE_MD.finditer(text):
      result += escape(text[last:m.start()])
      if m.group(2):   # ***bold+italic***
          result += f"[bold italic]{escape(m.group(2))}[/bold italic]"
      elif m.group(3): # **bold**
          result += f"[bold]{escape(m.group(3))}[/bold]"
      elif m.group(4): # *italic*
          result += f"[italic]{escape(m.group(4))}[/italic]"
      elif m.group(5): # `code`
          result += f"[bold #ff8c00]{escape(m.group(5))}[/bold #ff8c00]"
      last = m.end()
  result += escape(text[last:])
  return result


def _render_markdown_no_bg(text: str) -> None:
  """
  Рендерит markdown без цветных фонов у code-блоков.
  Fenced code → dim серый текст с отступом.
  Inline code → оранжевый bold.
  **Bold**, *italic* → Rich-форматирование.
  """
  last = 0
  for m in _CODE_FENCE.finditer(text):
      before = text[last:m.start()]
      if before.strip():
          _render_plain(before)
      code = m.group(1).rstrip()
      for line in code.splitlines():
          console.print(f"  [dim #888888]{escape(line)}[/dim #888888]")
      last = m.end()
  tail = text[last:]
  if tail.strip():
      _render_plain(tail)

def _render_plain(text: str) -> None:
  """Рендерит обычный текст: **bold**, *italic*, `inline-code`, заголовки, списки."""
  for line in text.splitlines():
      stripped = line.strip()
      if not stripped:
          console.print()
          continue
      # Заголовки
      if stripped.startswith("### "):
          console.print(f"[bold]{_apply_inline(stripped[4:])}[/bold]")
      elif stripped.startswith("## "):
          console.print(f"[bold]{_apply_inline(stripped[3:])}[/bold]")
      elif stripped.startswith("# "):
          console.print(f"[bold {ORANGE}]{_apply_inline(stripped[2:])}[/bold {ORANGE}]")
      # Нумерованные списки
      elif re.match(r'^\d+\.\s', stripped):
          m = re.match(r'^(\d+\.\s)(.*)', stripped)
          console.print(f"[bold {ORANGE}]{escape(m.group(1))}[/bold {ORANGE}]{_apply_inline(m.group(2))}")
      # Маркированные списки
      elif stripped.startswith(("- ", "* ", "• ")):
          body = stripped[2:]
          console.print(f"  [dim {ORANGE}]•[/dim {ORANGE}] {_apply_inline(body)}")
      else:
          console.print(_apply_inline(stripped))


# ─── Agent response ────────────────────────────────────────────────────────────

def print_agent_message(text: str, agent_name: str = "") -> None:
  text = text.strip()
  if not text:
      return
  console.print()

  lines = text.split("\n", 1)
  first_line = lines[0].strip()
  rest = lines[1].strip() if len(lines) > 1 else ""

  prefix = f"[bold {ORANGE}]●[/bold {ORANGE}]"
  name_part = f" [dim {GRAY}]{escape(agent_name)}[/dim {GRAY}] " if agent_name else " "
  console.print(f"{prefix}{name_part}{_apply_inline(first_line)}")

  if rest:
      _render_markdown_no_bg(rest)

  console.print()


def print_status_line(label: str, detail: str = "", color: str = ORANGE) -> None:
  detail = detail.strip()
  if detail:
      console.print(f"[bold {color}]●[/bold {color}] [dim {GRAY}]{escape(label)}[/dim {GRAY}] [dim #666666]{escape(detail)}[/dim #666666]")
  else:
      console.print(f"[bold {color}]●[/bold {color}] [dim {GRAY}]{escape(label)}[/dim {GRAY}]")


# ─── Thinking / STEP block ────────────────────────────────────────────────────

def print_step(text: str) -> None:
  print_status_line("Thinking", text, color="#666666")

def print_step_block(text: str) -> None:
  print_step(text)

def render_status_line(label: str, text: str = "", color: str = ORANGE) -> str:
  body = text.strip()
  if body:
      return f"[bold {color}]●[/bold {color}] [dim {GRAY}]{escape(label)}[/dim {GRAY}] [dim #666666]{escape(body)}[/dim #666666]"
  return f"[bold {color}]●[/bold {color}] [dim {GRAY}]{escape(label)}[/dim {GRAY}]"

def print_status(label: str, text: str = "", color: str = ORANGE) -> None:
  print_status_line(label, text, color=color)


class StatusSpinner:
  def __init__(self, label: str, detail: str = ""):
      self.label = label
      self.detail = detail
      self._stop = threading.Event()
      self._thread = None

  def start(self) -> None:
      import sys as _sys
      import time as _time
      _FRAMES = ["◐", "◓", "◑", "◒"]
      _ANSI_COLORS = [
          "\033[38;2;180;60;0m", "\033[38;2;210;90;0m",
          "\033[38;2;255;140;0m", "\033[38;2;230;110;0m",
      ]
      _RST = "\033[0m"; _DIM = "\033[2m"; _BOLD = "\033[1m"
      label = self.label; detail = self.detail; stop_ev = self._stop
      _start = _time.time()

      def _run():
          i = 0
          while not stop_ev.is_set():
              color = _ANSI_COLORS[i % len(_ANSI_COLORS)]
              frame = _FRAMES[i % len(_ANSI_COLORS)]
              elapsed = int(_time.time() - _start)
              label_part = f" {_DIM}{label}{_RST}" if label else ""
              detail_part = f" {_DIM}{detail}{_RST}" if detail else ""
              time_part = f" {_DIM}\033[38;2;80;80;80m{elapsed}s{_RST}" if elapsed >= 1 else ""
              _sys.stdout.write(f"\r  {_BOLD}{color}{frame}{_RST}{label_part}{detail_part}{time_part}  ")
              _sys.stdout.flush()
              i += 1
              stop_ev.wait(0.12)

      self._thread = threading.Thread(target=_run, daemon=True)
      self._thread.start()

  def stop(self) -> None:
      import sys as _sys
      self._stop.set()
      if self._thread:
          self._thread.join(timeout=0.5)
      _sys.stdout.write("\r\033[K")
      _sys.stdout.flush()


# ─── Shell / tool execution ───────────────────────────────────────────────────

def print_shell_cmd(cmd: str) -> None:
    import sys as _sys
    short = cmd.strip()
    if len(short) > 90:
        short = short[:87] + "..."
    # §PATCH-3 no newline — output erases this line in-place
    _sys.stdout.write("  > " + short + "\r")
    _sys.stdout.flush()

def print_shell_output(out: str, err: str, max_lines: int = 6) -> None:
      import sys as _sys
      # §PATCH-3 erase cmd line, no more spam
      _sys.stdout.write("\033[2K\r")
      _sys.stdout.flush()
      out_lines = out.strip().splitlines() if out.strip() else []
      err_lines = err.strip().splitlines() if err.strip() else []
      all_lines: list[tuple[str, str]] = (
          [(l, "out") for l in out_lines] + [(l, "err") for l in err_lines]
      )
      if not all_lines:
          return
      shown = all_lines[:max_lines]
      for line, kind in shown:
          text = escape(line[:130])
          if kind == "err":
              console.print(f"  [dim #995555]{text}[/dim #995555]")
          else:
              console.print(f"  [dim #666666]{text}[/dim #666666]")
      extra = len(all_lines) - max_lines
      if extra > 0:
          console.print(f"  [dim #444444]... +{extra} lines[/dim #444444]")
def print_skill_header(skill_name: str, query: str = "") -> None:
  q_part = f" [dim #666666]{escape(query[:60])}[/dim #666666]" if query else ""
  console.print(
      f"  [bold {ORANGE}]~[/bold {ORANGE}] "
      f"[dim {GRAY}]{escape(skill_name)}[/dim {GRAY}]{q_part}"
  )


def reset_cmd_display(line_count: int = 1) -> None:
  """Стирает N последних строк — для in-place замены строки команды."""
  import sys
  for _ in range(line_count):
      sys.stdout.write("\033[1A\r\033[K")
  sys.stdout.flush()


# ─── System / separator ────────────────────────────────────────────────────────

def print_separator() -> None:
  console.print("─" * 54, style=f"dim {GRAY}")

def print_thinking(frame: str) -> None:
  console.print(f"  [dim italic {GRAY}]{escape(frame)}[/dim italic {GRAY}]")

def print_user_line(text: str) -> None:
  console.print(f"[bold {WHITE}]>[/bold {WHITE}] {escape(text)}")

def print_poll(question: str, options: list[tuple[str, str]]) -> str:
  console.print(f"\n[bold {ORANGE}]?[/bold {ORANGE}] {escape(question)}")
  for idx, (opt_text, hint) in enumerate(options, 1):
      hint_part = f"  [dim]– {escape(hint)}[/dim]" if hint else ""
      console.print(f"  [{WHITE}]{idx}.[/{WHITE}] {escape(opt_text)}{hint_part}")
  console.print()
  while True:
      try:
          raw = input("  → ").strip()
          if raw.isdigit() and 1 <= int(raw) <= len(options):
              return options[int(raw) - 1][0]
          console.print(f"  [dim]Введи число 1–{len(options)}[/dim]")
      except (EOFError, KeyboardInterrupt):
          return options[-1][0]

def print_suggest_next(text: str) -> None:
  """Рендерит SUGGEST_NEXT — жирная последняя строка ответа агента."""
  console.print()
  console.print(f"[bold]{escape(text)}[/bold]")
