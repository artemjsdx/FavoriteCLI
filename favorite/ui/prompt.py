from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.filters import is_done

from .theme import STYLE


ALL_COMMANDS = [
  ("/Favorite API",    "Управление ключами FavoriteAPI"),
  ("/OpenRouter API",  "Управление ключами OpenRouter"),
  ("/models",          "Все модели всех провайдеров"),
  ("/agents",          "Управление роем агентов"),
  ("/auto",            "Режим глубокой автоматизации"),
  ("/new session",     "Начать новую сессию"),
  ("/session",         "Список сохранённых сессий"),
  ("/skills",          "Управление скиллами"),
  ("/plan",            "Режим обсуждения и планирования"),
  ("/build",           "Режим исполнения"),
  ("/reset",           "Сбросить контекст диалога"),
  ("/silent",          "Включить/выключить режим тишины"),
  ("/export",          "Выгрузить сессию в zip/md"),
  ("/stop",            "Остановить /auto"),
  ("/resume",          "Продолжить остановленный /auto"),
  ("/architect",       "Режим архитектора (дорогая модель думает)"),
  ("/spec",            "Spec-Driven Development"),
  ("/usage",           "Статистика использования API"),
  ("/memory",          "Просмотр / редактирование Favorite.md"),
  ("/tasks",           "Управление задачами сессии"),
  ("/doctor",          "Диагностика системы"),
  ("/recap",           "Краткое резюме сессии"),
  ("/compact",         "Сжать контекст"),
  ("/effort",          "Уровень старания агента"),
  ("/map",             "Карта файлов проекта"),
  ("/branch",          "Форк диалога"),
  ("/image",           "Прикрепить изображение"),
  ("/voice",           "Голосовой ввод/вывод"),
  ("/soul",            "Soul-режим (непрерывная работа)"),
  ("/feedback",        "Журнал ошибок и мыслей агента"),
  ("/snapshot",        "Снимок состояния проекта"),
  ("/modules",         "Список активных модулей"),
  ("/sandbox",         "Изолированная песочница"),
  ("/parallel",        "Параллельный /auto: unified|independent|hybrid (§19.2)"),
  ("/tour",            "Перезапустить онбординг-тур (§17.21)"),
]


# ── Tab registry (§18.4) ──────────────────────────────────────────────────────
# Maps slot index (1–9) → label string shown in prompt
_TAB_REGISTRY: dict[int, str] = {1: "M1"}


def register_tab(slot: int, label: str) -> None:
    """Register an agent tab at slot 1–9. Called from agents_cmd on spawn."""
    if 1 <= slot <= 9:
        _TAB_REGISTRY[slot] = label


def get_tab_label(slot: int = 1) -> str:
    """Return label for given tab slot, or empty string if not registered."""
    return _TAB_REGISTRY.get(slot, "")


def get_active_tab() -> int:
    """Return currently active tab slot (1-based)."""
    return _ACTIVE_TAB[0]


def set_active_tab(slot: int) -> None:
    """Set active tab. Slot 1 = main agent."""
    if 1 <= slot <= 9:
        _ACTIVE_TAB[0] = slot


_ACTIVE_TAB: list[int] = [1]  # mutable container so closures can write


class SlashCompleter(Completer):
  def get_completions(self, document, complete_event):
      text = document.text_before_cursor
      # Автодополнение только в первой строке
      if "\n" in text:
          return
      if not text.startswith("/"):
          return
      partial = text.lower()
      starts, contains = [], []
      for cmd, desc in ALL_COMMANDS:
          low = cmd.lower()
          if low.startswith(partial):
              starts.append((cmd, desc))
          elif partial[1:] and partial[1:] in low:
              contains.append((cmd, desc))
      seen = set()
      for cmd, desc in starts + contains:
          if cmd in seen:
              continue
          seen.add(cmd)
          yield Completion(
              cmd,
              start_position=-len(text),
              display=_highlight(cmd, text),
              display_meta=desc,
          )


def _highlight(cmd: str, partial: str) -> HTML:
  low_cmd, low_partial = cmd.lower(), partial.lower()
  result, i = "", 0
  while i < len(cmd):
      if low_partial and low_cmd[i:i+len(low_partial)] == low_partial:
          result += f"<style fg='#ff8c00'><b>{cmd[i:i+len(low_partial)]}</b></style>"
          i += len(low_partial)
      else:
          result += cmd[i]
          i += 1
  return HTML(result)


def build_session(on_export=None, on_tab_switch=None) -> PromptSession:
  """
  Мультистрочный ввод:
    Enter      — перенос строки (вставка \n)
    END        — отправить сообщение
    ESC        — очистить буфер
    ESC + END  — экспортировать сессию
    Ctrl+1..9  — переключение вкладок агентов (§18.4)
  """
  kb = KeyBindings()

  @kb.add("enter")
  def _newline(event):
      """Enter = новая строка внутри сообщения."""
      buf = event.app.current_buffer
      # Если это slash-команда (однострочная) — сразу отправляем
      if buf.text.startswith("/") and "\n" not in buf.text:
          buf.validate_and_handle()
      else:
          buf.insert_text("\n")

  @kb.add("end")
  def _submit(event):
      """END = отправить сообщение."""
      event.app.current_buffer.validate_and_handle()

  @kb.add("escape")
  def _noop(event):
      event.app.current_buffer.reset()

  @kb.add("escape", "end")
  def _export(event):
      if on_export:
          on_export()

  @kb.add("backspace")
  def _backspace_and_complete(event):
      buf = event.app.current_buffer
      if buf.complete_state:
          buf.cancel_completion()
      buf.delete_before_cursor(count=1)
      if buf.text.startswith("/") and "\n" not in buf.text:
          buf.start_completion(select_first=False)

  # ── §18.4 — Ctrl+1..9 tab switching ──────────────────────────
  def _make_tab_handler(slot: int):
      @kb.add(f"c-{slot}")
      def _tab_switch(event):
          label = get_tab_label(slot)
          if not label:
              return  # slot not registered
          set_active_tab(slot)
          if on_tab_switch:
              on_tab_switch(slot, label)
          # Show tab indicator in toolbar area
          try:
              from rich.console import Console as _Con
              _Con().print(f"\n  [bold #ff8c00][ Таб → {label} ][/bold #ff8c00]\n")
          except Exception:
              pass
      return _tab_switch

  for _s in range(1, 10):
      _make_tab_handler(_s)

  return PromptSession(
      completer=SlashCompleter(),
      style=STYLE,
      key_bindings=kb,
      history=InMemoryHistory(),
      complete_while_typing=True,
      mouse_support=False,
      multiline=True,
  )


def get_prompt_tokens():
  return [("class:prompt-arrow", "\u276f ")]
