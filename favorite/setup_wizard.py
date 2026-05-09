"""
Мастер первоначальной настройки FavoriteCLI.
Запускается автоматически если нет ни одного API-ключа.
"""
from rich.console import Console
from rich.panel import Panel

console = Console()

_ORANGE = "bold #ff8c00"
_GRAY   = "dim"

_SENTINEL = object()   # маркер «пользователь нажал Ctrl+C»


def _ask(prompt: str, required: bool = False):
  """
  Запрашивает ввод.
  Возвращает строку, "" (Enter без текста), или _SENTINEL (Ctrl+C / EOF).
  """
  while True:
      try:
          val = input(f"  {prompt}: ").strip()
      except (EOFError, KeyboardInterrupt):
          console.print()          # перенос строки после ^C
          return _SENTINEL
      if val or not required:
          return val
      console.print("  [red]Поле обязательно. Попробуй ещё раз.[/red]")


def run_setup(cfg) -> bool:
  """
  Интерактивный мастер настройки.
  Возвращает True если минимальная конфигурация задана.
  """
  console.print()
  console.print(Panel(
      "[bold #ff8c00]Добро пожаловать в FavoriteCLI![/bold #ff8c00]\n\n"
      "[dim]Ключи API не найдены. Давай настроим всё за пару минут.\n"
      "Данные сохраняются локально в [/dim][white]config/[/white][dim] и никуда не отправляются.\n"
      "Ctrl+C в любой момент — пропустить шаг.[/dim]",
      border_style="#ff8c00",
      expand=False,
      width=58,
  ))
  console.print()

  # --- OpenRouter ---
  console.print(f"[{_ORANGE}]1. OpenRouter API[/{_ORANGE}]")
  console.print(f"[{_GRAY}]   Получить ключ: https://openrouter.ai → Keys[/{_GRAY}]")
  console.print(f"[{_GRAY}]   Формат: sk-or-v1-...[/{_GRAY}]")
  or_key = _ask("Вставь ключ OpenRouter (Enter — пропустить)")
  if or_key is _SENTINEL or not or_key:
      console.print(f"  [{_GRAY}]Пропущено.[/{_GRAY}]")
  else:
      model = _ask("Модель по умолчанию [qwen/qwen3-coder:free]")
      if model is _SENTINEL:
          model = "qwen/qwen3-coder:free"
      cfg.add_openrouter_key(or_key, label="default", model=model or "qwen/qwen3-coder:free")
      console.print(f"  [green]OpenRouter добавлен.[/green]")

  console.print()

  # --- FavoriteAPI ---
  console.print(f"[{_ORANGE}]2. FavoriteAPI[/{_ORANGE}]")
  console.print(f"[{_GRAY}]   Локальный прокси к Gemini (запускается отдельно).[/{_GRAY}]")
  fav_key = _ask("Вставь ключ FavoriteAPI (Enter — пропустить)")
  if fav_key is _SENTINEL or not fav_key:
      console.print(f"  [{_GRAY}]Пропущено.[/{_GRAY}]")
  else:
      base_url = _ask("Адрес сервера [http://127.0.0.1:5005]")
      if base_url is _SENTINEL or not base_url:
          base_url = "http://127.0.0.1:5005"
      cfg.set_favorite_api_base_url(base_url)
      cfg.add_favorite_key(fav_key, label="default")
      console.print(f"  [green]FavoriteAPI добавлен.[/green]")

  console.print()

  # --- VoidAI ---
  console.print(f"[{_ORANGE}]3. VoidAI (для скилла WebSearch)[/{_ORANGE}]")
  void_key = _ask("Вставь ключ VoidAI (Enter — пропустить)")
  if void_key is _SENTINEL or not void_key:
      console.print(f"  [{_GRAY}]Пропущено. Поиск будет через DuckDuckGo.[/{_GRAY}]")
  else:
      cfg.set_void_ai_key(void_key)
      console.print(f"  [green]VoidAI добавлен.[/green]")

  console.print()

  # --- GitHub ---
  console.print(f"[{_ORANGE}]4. GitHub (для авто-пуша кода)[/{_ORANGE}]")
  gh_token = _ask("Вставь GitHub токен (Enter — пропустить)")
  if gh_token is _SENTINEL or not gh_token:
      console.print(f"  [{_GRAY}]Пропущено. Авто-пуш недоступен.[/{_GRAY}]")
  else:
      gh_owner = _ask("GitHub логин (username)")
      if gh_owner is _SENTINEL or not gh_owner:
          console.print(f"  [red]Логин не указан, GitHub не сохранён.[/red]")
      else:
          gh_repo = _ask("Репозиторий [FavoriteCLI]")
          if gh_repo is _SENTINEL or not gh_repo:
              gh_repo = "FavoriteCLI"
          cfg.set_github(token=gh_token, owner=gh_owner, repo=gh_repo)
          console.print(f"  [green]GitHub настроен: {gh_owner}/{gh_repo}[/green]")

  console.print()

  if not cfg.has_any_provider():
      console.print(
          "[yellow]Ни одного провайдера не добавлено.[/yellow]\n"
          "[dim]Добавь ключи через /Favorite API или /OpenRouter API в любой момент.[/dim]"
      )
      return False

  console.print(f"[{_ORANGE}]Настройка завершена![/{_ORANGE}] Запускаю FavoriteCLI...\n")
  return True
