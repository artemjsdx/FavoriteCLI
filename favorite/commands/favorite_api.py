from .base import ICommand, CommandContext
from ..ui.chat import print_agent_message, print_separator, print_status_line
from ..ui.welcome import print_info


class FavoriteApiCommand(ICommand):
  name = "/Favorite API"
  description = "Управление ключами FavoriteAPI"
  priority = 1

  def execute(self, args: str, ctx: CommandContext) -> None:
    cfg = ctx.config
    while True:
        from rich.console import Console as _Con
        from rich.markup import escape as _esc
        _con = _Con()
        _ORANGE = "#ff8c00"; _DIM = "#555555"; _DIM2 = "#2a2a2a"
        _W = 52
        _con.print()
        _con.print("[dim #2a2a2a]╭──[/dim #2a2a2a] [bold #ff8c00]◈ FAVORITE API[/bold #ff8c00] [dim #2a2a2a]" + "─" * (_W - 16) + "╮[/dim #2a2a2a]")
        _con.print("[dim #2a2a2a]│[/dim #2a2a2a]")
        keys = cfg.favorite_api_keys
        if not keys:
            _con.print("[dim #2a2a2a]│[/dim #2a2a2a]  [dim #555555]ключи не добавлены[/dim #555555]")
        else:
            for i, k in enumerate(keys, 1):
                key_str = k["key"]
                masked = key_str[:8] + "..." + key_str[-4:] if len(key_str) > 14 else "***"
                model   = _esc(k.get("model") or "—")
                default_mark = "  [bold #5fd7af]✓[/bold #5fd7af]" if k.get("is_default") else ""
                _con.print("[dim #2a2a2a]│[/dim #2a2a2a]  [dim #555555]" + str(i) + ".[/dim #555555]  [white]" + _esc(masked) + "[/white]" + default_mark)
                _con.print("[dim #2a2a2a]│[/dim #2a2a2a]     [dim #555555]model [dim #333333]·[/dim #333333] [#ff8c00]" + model + "[/#ff8c00][/dim #555555]")
        bridge_status = "настроен" if cfg.has_tg_bridge() else "не настроен"
        _con.print("[dim #2a2a2a]│[/dim #2a2a2a]")
        _con.print("[dim #2a2a2a]│[/dim #2a2a2a]  [dim #555555]1.[/dim #555555]  добавить ключ")
        _con.print("[dim #2a2a2a]│[/dim #2a2a2a]  [dim #555555]2.[/dim #555555]  удалить ключ")
        _con.print("[dim #2a2a2a]│[/dim #2a2a2a]  [dim #555555]3.[/dim #555555]  адрес сервера  [dim #555555]" + _esc(cfg.favorite_api_base_url) + "[/dim #555555]")
        _con.print("[dim #2a2a2a]│[/dim #2a2a2a]  [dim #555555]4.[/dim #555555]  Telegram-мост  [dim #555555]" + bridge_status + "[/dim #555555]")
        if keys:
            _con.print("[dim #2a2a2a]│[/dim #2a2a2a]  [dim #555555]5.[/dim #555555]  задать модель")
        _con.print("[dim #2a2a2a]│[/dim #2a2a2a]  [dim #555555]0.[/dim #555555]  [dim #555555]назад[/dim #555555]")
        _con.print("[dim #2a2a2a]│[/dim #2a2a2a]")
        _con.print("[dim #2a2a2a]" + "╰" + "─" * (_W + 2) + "╯[/dim #2a2a2a]")
        try:
            choice = input("  Выбери: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if choice == "0":
            break
        elif choice == "1":
            try:
                key_val = input("  Ключ (fa_sk_...): ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if not key_val:
                print_info("  Пусто — отменено.")
                continue
            try:
                model_val = input("  Название модели (Enter — пропустить, сервер выберет сам): ").strip()
            except (EOFError, KeyboardInterrupt):
                model_val = ""
            cfg.add_favorite_key(key_val, model=model_val or None)
            print_status_line("Key Added", model_val or "сервер выберет модель", color="#ff8c00")
        elif choice == "2":
            keys = cfg.favorite_api_keys
            if not keys:
                print_info("  Нечего удалять.")
                continue
            try:
                n = input("  Номер ключа для удаления: ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if n.isdigit() and cfg.remove_favorite_key(int(n) - 1):
                print_status_line("Key Removed", color="#666666")
            else:
                print_info("  Неверный номер.")
        elif choice == "3":
            try:
                url = input(f"  Новый адрес [{cfg.favorite_api_base_url}]: ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if url:
                cfg.set_favorite_api_base_url(url)
                print_info(f"  Адрес обновлён: {url}")
        elif choice == "4":
            print_info("  TG-мост: при потере связи CLI сам найдёт новый URL через Telegram.")
            print_info("  Токен бота и Chat ID — те же что в .env FavoriteAPI (TG_NOTIFY_TOKEN, TG_NOTIFY_CHATS).")
            try:
                cur_tok = cfg.tg_bridge_token
                cur_cid = cfg.tg_bridge_chat_id
                tg_tok = input(f"  Токен бота [{cur_tok[:8]+'...' if cur_tok else 'нет'}]: ").strip()
                tg_cid = input(f"  Chat ID [{cur_cid or 'нет'}]: ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if tg_tok and tg_cid:
                cfg.set_tg_bridge(tg_tok, tg_cid)
                print_status_line("TG Bridge", "сохранён — URL подтянется при обрыве", color="#ff8c00")
            else:
                print_info("  Отменено (нужны оба поля).")
        elif choice == "5":
            keys = cfg.favorite_api_keys
            if not keys:
                print_info("  Нет ключей.")
                continue
            if len(keys) > 1:
                try:
                    n = input("  Номер ключа: ").strip()
                except (EOFError, KeyboardInterrupt):
                    continue
                if not n.isdigit() or int(n) < 1 or int(n) > len(keys):
                    print_info("  Неверный номер.")
                    continue
                idx = int(n) - 1
            else:
                idx = 0
            try:
                model_val = input("  Название модели (Enter — сбросить на дефолт): ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            cfg.set_favorite_key_model(idx, model_val or None)
            if model_val:
                print_status_line("Model Set", model_val, color="#ff8c00")
            else:
                print_status_line("Model Reset", "сервер выбирает сам", color="#666666")
