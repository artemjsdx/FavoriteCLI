from __future__ import annotations
from typing import Optional
import json
from pathlib import Path
from .base import ICommand, CommandContext
from rich.console import Console
from rich.markup import escape
from rich.text import Text

_ROLES_FILE = Path(__file__).resolve().parent.parent / "agent" / "sub_roles_library.json"
_UA_FILE    = Path(__file__).resolve().parent.parent.parent / "config" / "user_agents.json"

console = Console()
_SEP = "[dim #2a2a2a]" + "─" * 50 + "[/dim #2a2a2a]"

_TAG_COLORS: dict[str, str] = {
  "search": "#5fafff", "web": "#5fafff",
  "code": "#5fd7af", "review": "#5fd7af",
  "security": "#ff5f87",
  "docs": "#af87ff",
  "testing": "#87d7ff",
  "performance": "#ffaf5f",
  "ux": "#ff87af", "ui": "#ff87af",
  "ideas": "#d7ff87", "creative": "#d7ff87",
  "cleanup": "#afd7af", "refactor": "#afd7af",
  "android": "#5fafff", "termux": "#5fafff",
  "architecture": "#ffdf87", "design": "#ffdf87",
  "critique": "#ff8787",
}


def load_roles() -> list[dict]:
  if not _ROLES_FILE.exists(): return []
  try: return json.loads(_ROLES_FILE.read_text(encoding="utf-8"))
  except Exception: return []


def load_ua() -> dict:
  if not _UA_FILE.exists():
    return {"main": {"name": "Главный агент", "active": True, "model": None, "custom_prompt": None}, "agents": []}
  try:
    data = json.loads(_UA_FILE.read_text(encoding="utf-8"))
    if "agents" not in data: data["agents"] = []
    return data
  except Exception:
    return {"main": {"name": "Главный агент", "active": True, "model": None, "custom_prompt": None}, "agents": []}


def save_ua(data: dict) -> None:
  _UA_FILE.parent.mkdir(parents=True, exist_ok=True)
  _UA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _pill(tag: str) -> str:
  c = _TAG_COLORS.get(tag, "#555555")
  return f"[{c}]{escape(tag)}[/{c}]"


def _sep() -> None:
  console.print(_SEP)


def _pick(prompt: str = "  → ") -> str:
  try: return input(prompt).strip()
  except (EOFError, KeyboardInterrupt): return "0"


def _mask_key(key: str) -> str:
  if len(key) > 14: return key[:8] + "…" + key[-4:]
  return "***"


def _get_model_label(model_id: str | None) -> str:
  if not model_id: return "авто"
  return model_id.split("/")[-1]


def _status_text(active: bool) -> tuple[str, str]:
  return ("#5fd7af", "active") if active else ("#666666", "inactive")


def _get_or_model_label(ctx: CommandContext) -> str:
  try:
    or_key = ctx.config.default_openrouter_key()
    if or_key: return or_key.get("model", "?").split("/")[-1]
    fav_key = ctx.config.default_favorite_key()
    if fav_key: return (fav_key.get("model") or "FavoriteAPI").split("/")[-1]
  except Exception: pass
  return "нет API"


def _pick_fav_models(api_key: str, ctx: CommandContext) -> tuple[list[str], str]:
    """
    Fetch models from FavoriteAPI.
    1) Try stored base_url; 2) TG bridge fallback if configured.
    Returns (model_ids, resolved_base_url).
    """
    from ..api.favorite_api import FavoriteApiClient
    from ..bridge import tg_url

    cfg = ctx.config
    base_url = cfg.favorite_api_base_url

    def _try_fetch(url: str) -> list[str]:
      client = FavoriteApiClient(api_key, base_url=url)
      raw = client.list_models()
      result: list[str] = []
      for m in raw:
        if isinstance(m, dict):
          mid = m.get("id") or m.get("name", "")
          if mid:
            result.append(mid)
        elif isinstance(m, str) and m:
          result.append(m)
      return result

    # --- attempt 1: stored URL ---
    try:
      models = _try_fetch(base_url)
      if models:
        return models, base_url
      console.print(f"  [dim #888888]Сервер {escape(base_url)} доступен, но вернул пустой список[/dim #888888]")
    except Exception as e:
      console.print(f"  [dim #888888]Сервер {escape(base_url)} недоступен: {escape(str(e)[:60])}[/dim #888888]")

    # --- attempt 2: TG bridge ---
    if not cfg.has_tg_bridge():
      console.print("  [dim #666666]TG-мост не настроен (настрой через /Favorite API → 4)[/dim #666666]")
      return [], base_url

    console.print("  [dim #888888]TG-мост: запрашиваю URL...[/dim #888888]")
    try:
      fresh_url = tg_url.fetch_url(cfg.tg_bridge_token, cfg.tg_bridge_chat_id)
      if not fresh_url:
        console.print("  [dim #666666]TG-мост: URL не найден (пиннед сообщение пусто или нет text_link)[/dim #666666]")
        return [], base_url
      console.print(f"  [dim #5fafff]TG-мост: URL → {escape(fresh_url)}[/dim #5fafff]")
      if fresh_url != base_url:
        cfg.set_favorite_api_base_url(fresh_url)
      models = _try_fetch(fresh_url)
      if models:
        return models, fresh_url
      console.print("  [dim #888888]TG URL доступен, но список моделей пустой[/dim #888888]")
    except Exception as e:
      console.print(f"  [dim #666666]TG-мост ошибка: {escape(str(e)[:80])}[/dim #666666]")

    return [], base_url

def _pick_provider_and_model(ctx: CommandContext) -> dict | None | str:
  """
  Provider → API key → Model picker.
  Returns {"provider", "key", "model"} | None (auto) | "cancel".
  """
  # ── Step 1: provider ────────────────────────────────────────────
  console.print()
  console.print("  [bold white]Шаг 1 — Провайдер[/bold white]")
  console.print()
  console.print("  [dim #666666]1.[/dim #666666]  [#5fafff]OpenRouter[/#5fafff]")
  console.print("  [dim #666666]2.[/dim #666666]  [#ff8c00]FavoriteAPI[/#ff8c00]")
  console.print("  [dim #666666]0.[/dim #666666]  [dim]Авто (глобальный ключ из настроек)[/dim]")
  _sep()
  ch = _pick()
  if ch == "": return "cancel"
  if ch == "0": return None
  if ch == "1": provider = "openrouter"
  elif ch == "2": provider = "favoriteapi"
  else: return "cancel"

  # ── Step 2: API key ────────────────────────────────────────
  existing = ctx.config.openrouter_keys if provider == "openrouter" else ctx.config.favorite_api_keys
  pname = "OpenRouter" if provider == "openrouter" else "FavoriteAPI"
  console.print()
  console.print(f"  [bold white]Шаг 2 — API ключ[/bold white]  [dim]({pname})[/dim]")
  console.print()
  chosen_key: str | None = None
  if existing:
    for i, k in enumerate(existing, 1):
      masked = _mask_key(k["key"])
      mhint = f"  [dim]{escape(k['model'])}[/dim]" if k.get("model") else ""
      dflt = "  [dim #ff8c00][дефолт][/dim #ff8c00]" if k.get("is_default") else ""
      console.print(f"  [dim #666666]{i}.[/dim #666666]  [dim]{masked}[/dim]{mhint}{dflt}")
    console.print()
    n = len(existing) + 1
    console.print(f"  [dim #666666]{n}.[/dim #666666]  [dim #5fafff]Ввести новый ключ[/dim #5fafff]")
    console.print("  [dim #666666]0.[/dim #666666]  [dim]Отмена[/dim]")
    _sep()
    kch = _pick()
    if kch in ("", "0"): return "cancel"
    if kch == str(n):
      hint = "sk-or-v1-..." if provider == "openrouter" else "fa_sk_..."
      chosen_key = _pick(f"  Ключ ({hint}): ")
      if not chosen_key or chosen_key == "0": return "cancel"
    elif kch.isdigit() and 1 <= int(kch) <= len(existing):
      chosen_key = existing[int(kch) - 1]["key"]
    else: return "cancel"
  else:
    hint = "sk-or-v1-..." if provider == "openrouter" else "fa_sk_..."
    console.print(f"  [dim]Нет сохранённых ключей. Введи:[/dim]")
    chosen_key = _pick(f"  Ключ ({hint}): ")
    if not chosen_key or chosen_key == "0": return "cancel"

  # ── Step 3: model ──────────────────────────────────────────
  chosen_model: str | None = None
  if provider == "openrouter":
    from ..commands.openrouter_api import _pick_model_menu as _or_pick
    console.print()
    console.print("  [dim]Загружаю список моделей с OpenRouter…[/dim]")
    chosen_model = _or_pick(chosen_key)
  else:
    console.print()
    console.print(f"  [dim]Запрос моделей с FavoriteAPI ({escape(ctx.config.favorite_api_base_url)})…[/dim]")
    fav_models, _resolved_url = _pick_fav_models(chosen_key, ctx)
    if fav_models:
      console.print()
      console.print("  [bold white]Шаг 3 — Модель[/bold white]")
      console.print()
      for i, mid in enumerate(fav_models, 1):
        console.print(f"  [dim #666666]{i:>2}.[/dim #666666]  [white]{escape(mid)}[/white]")
      console.print()
      nf = len(fav_models) + 1
      console.print(f"  [dim #666666]{nf}.[/dim #666666]  [dim]Ввести вручную[/dim]")
      console.print("  [dim #666666] 0.[/dim #666666]  [dim]Авто (сервер выберет сам)[/dim]")
      _sep()
      mch = _pick()
      if mch == "0": chosen_model = None
      elif mch == str(nf):
        v = _pick("  Модель: ")
        chosen_model = v if v and v != "0" else None
      elif mch.isdigit() and 1 <= int(mch) <= len(fav_models):
        chosen_model = fav_models[int(mch) - 1]
    else:
      console.print("  [dim]Сервер недоступен или не вернул список. Введи ID модели вручную (Enter — авто):[/dim]")
      v = _pick("  > ")
      chosen_model = v if v and v != "0" else None

  return {"provider": provider, "key": chosen_key, "model": chosen_model}


def _next_agent_id(ua: dict) -> str:
  agents = ua.get("agents", [])
  ids = {a["id"] for a in agents}
  i = 1
  while f"agent-{i}" in ids: i += 1
  return f"agent-{i}"


def _get_role_name(role_id: str) -> str:
  if not role_id: return ""
  roles = load_roles()
  for r in roles:
    if r.get("id") == role_id: return r.get("name", "")
  return role_id


class AgentsCommand(ICommand):
  name = "/agents"
  description = "Управление агентами"
  priority = 4

  def execute(self, args: str, ctx: CommandContext) -> None:
    self._main_menu(ctx)

  # ── Main menu ──────────────────────────────────────────────────

  def _main_menu(self, ctx: CommandContext) -> None:
    while True:
      ua = load_ua()
      agents = ua.get("agents", [])
      mc = ua.get("main", {})
      console.print()
      h = Text("  ")
      h.append("◈ ", style="bold #ff8c00")
      h.append("Агенты", style="bold white")
      console.print(h)
      console.print()
      _sep()
      console.print()
      main_active = mc.get("active", True)
      sc, ss = _status_text(main_active)
      m_label = _get_model_label(mc.get("model")) if mc.get("model") else _get_or_model_label(ctx)
      prov_label = ""
      if mc.get("provider"): prov_label = f"  [dim #555555]{mc['provider']}[/dim #555555]"
      row = Text("  ")
      row.append("1.", style="dim #666666")
      row.append("  main-1", style="bold cyan")
      row.append(f"  ·  {mc.get('name', 'Главный агент')}", style="white")
      row.append(f"  [{ss}]", style=f"dim {sc}")
      row.append(f"  {m_label}", style="dim #ff8c00")
      console.print(row)
      if prov_label: console.print(f"      {prov_label}")
      for i, agent in enumerate(agents, 2):
        role_id = agent.get("role_id", "")
        sc2, ss2 = _status_text(agent.get("active", True))
        m_label2 = _get_model_label(agent.get("model"))
        p2 = f"  [dim #555555]{agent['provider']}[/dim #555555]" if agent.get("provider") else ""
        row2 = Text("  ")
        row2.append(f"{i}.", style="dim #666666")
        row2.append(f"  {agent.get('id','')}", style="bold cyan")
        row2.append(f"  ·  {agent.get('name', role_id)}", style="white")
        row2.append(f"  [{ss2}]", style=f"dim {sc2}")
        if role_id: row2.append(f"  ({role_id})", style="dim #444444")
        row2.append(f"  {m_label2}", style="dim #ff8c00")
        console.print(row2)
        if p2: console.print(f"      {p2}")
      console.print()
      _sep()
      n = len(agents) + 2
      console.print(f"  [dim #666666]{n}.[/dim #666666]  [dim #5fafff]+ Создать агента[/dim #5fafff]")
      console.print()
      console.print(f"  [dim #666666]m.[/dim #666666]  [dim #af87ff]Матрица возможностей[/dim #af87ff]")
      console.print(f"  [dim #666666]p.[/dim #666666]  [dim #af87ff]Пир-агенты[/dim #af87ff]")
      console.print(f"  [dim #666666]b.[/dim #666666]  [dim #af87ff]Групповое действие[/dim #af87ff]")
      console.print("  [dim #444444]0  выйти[/dim #444444]")
      console.print()
      ch = _pick()
      if ch in ("0", ""): return
      if ch == "1": self._edit_main(ctx)
      elif ch == str(n): self._create_agent(ctx)
      elif ch.isdigit():
        idx = int(ch) - 2
        if 0 <= idx < len(agents): self._edit_agent(agents[idx], ctx)

  # ── Edit main-1 ───────────────────────────────────────────────

  def _edit_main(self, ctx: CommandContext) -> None:
    while True:
      ua = load_ua()
      mc = ua.setdefault("main", {})
      name    = mc.get("name", "Главный агент")
      active  = mc.get("active", True)
      cprompt = mc.get("custom_prompt") or ""
      cur_model = mc.get("model")
      cur_prov  = mc.get("provider", "")
      cur_key   = mc.get("api_key", "")
      m_label = _get_model_label(cur_model) if cur_model else _get_or_model_label(ctx) + " (авто)"
      prov_hint = f"  [dim #555555]{cur_prov}[/dim #555555]" if cur_prov else "  [dim #444444]глобальный ключ[/dim #444444]"
      key_hint  = _mask_key(cur_key) if cur_key else ""
      sc, ss = _status_text(active)
      console.print()
      _sep()
      t = Text("  ")
      t.append("◆ ", style="bold #ff8c00")
      t.append("main-1", style="bold cyan")
      t.append(f"  ·  {name}", style="white")
      console.print(t)
      console.print()
      console.print(f"  [dim #666666]1.[/dim #666666]  Имя           [white]{escape(name)}[/white]")
      console.print(f"  [dim #666666]2.[/dim #666666]  Модель        [#ff8c00]{escape(m_label)}[/#ff8c00]{prov_hint}{'  ' + key_hint if key_hint else ''}")
      cp_hint = "(задан)" if cprompt else "(нет)"
      console.print(f"  [dim #666666]3.[/dim #666666]  Доп. промпт   [dim #888888]{cp_hint}[/dim #888888]")
      console.print(f"  [dim #666666]4.[/dim #666666]  Статус        [{sc}]{ss}[/{sc}]")
      console.print()
      _sep()
      console.print("  [dim #444444]0  назад[/dim #444444]")
      console.print()
      ch = _pick()
      if ch in ("0", ""): return
      elif ch == "1":
        console.print("  [dim]Новое имя:[/dim]")
        v = _pick("  > ")
        if v and v != "0": mc["name"] = v; save_ua(ua); console.print("  [#5fd7af]✓ Имя обновлено[/#5fd7af]")
      elif ch == "2":
        result = _pick_provider_and_model(ctx)
        if result == "cancel": continue
        if result is None:
          mc["model"] = None; mc["provider"] = None; mc["api_key"] = None
          save_ua(ua); console.print("  [#5fd7af]✓ Авто (глобальный ключ)[/#5fd7af]")
        else:
          mc["model"] = result["model"]; mc["provider"] = result["provider"]; mc["api_key"] = result["key"]
          save_ua(ua)
          lbl = _get_model_label(result["model"]) if result["model"] else "авто"
          console.print(f"  [#5fd7af]✓ Модель → {escape(lbl)}  [{escape(result['provider'])}][/#5fd7af]")
      elif ch == "3":
        console.print("  [dim]Доп. инструкции (пустая строка = сохранить):[/dim]")
        lines_in: list[str] = []
        while True:
          ln = _pick("  > ")
          if ln == "": break
          lines_in.append(ln)
        mc["custom_prompt"] = "\n".join(lines_in) if lines_in else None
        save_ua(ua)
        console.print(f"  [#5fd7af]✓ Промпт {'updated' if lines_in else 'cleared'}[/#5fd7af]")
      elif ch == "4":
        mc["active"] = not active; save_ua(ua)
        _, ns = _status_text(mc["active"])
        console.print(f"  [#5fd7af]✓ Статус → {ns}[/#5fd7af]")

  # ── Edit user agent ───────────────────────────────────────────

  def _edit_agent(self, agent: dict, ctx: CommandContext) -> None:
    aid = agent.get("id", "")
    while True:
      ua = load_ua()
      ref = next((a for a in ua.get("agents", []) if a.get("id") == aid), None)
      if not ref: return
      name     = ref.get("name", "")
      role_id  = ref.get("role_id", "")
      active   = ref.get("active", True)
      cur_model = ref.get("model")
      cur_prov  = ref.get("provider", "")
      cur_key   = ref.get("api_key", "")
      cprompt  = ref.get("custom_prompt") or ""
      m_label  = _get_model_label(cur_model) if cur_model else "авто"
      prov_hint = f"  [dim #555555]{cur_prov}[/dim #555555]" if cur_prov else "  [dim #444444]глобальный[/dim #444444]"
      key_hint  = _mask_key(cur_key) if cur_key else ""
      sc, ss = _status_text(active)
      console.print()
      _sep()
      t = Text("  ")
      t.append("◆ ", style="bold #ff8c00")
      t.append(aid, style="bold cyan")
      t.append(f"  ·  {name}", style="white")
      console.print(t)
      console.print()
      console.print(f"  [dim #666666]1.[/dim #666666]  Имя           [white]{escape(name)}[/white]")
      console.print(f"  [dim #666666]2.[/dim #666666]  Роль           [dim #888888]{escape(role_id)}[/dim #888888]  [dim #555555]{escape(_get_role_name(role_id))}[/dim #555555]")
      console.print(f"  [dim #666666]3.[/dim #666666]  Модель        [#ff8c00]{escape(m_label)}[/#ff8c00]{prov_hint}{'  ' + key_hint if key_hint else ''}")
      cp_hint = "(задан)" if cprompt else "(нет)"
      console.print(f"  [dim #666666]4.[/dim #666666]  Доп. промпт   [dim #888888]{cp_hint}[/dim #888888]")
      console.print(f"  [dim #666666]5.[/dim #666666]  Статус        [{sc}]{ss}[/{sc}]")
      console.print()
      console.print("  [dim #666666]d.[/dim #666666]  [dim #ff5f5f]Удалить агента[/dim #ff5f5f]")
      console.print()
      _sep()
      console.print("  [dim #444444]0  назад[/dim #444444]")
      console.print()
      ch = _pick()
      if ch in ("0", ""): return
      elif ch == "1":
        console.print("  [dim]Новое имя:[/dim]")
        v = _pick("  > ")
        if v and v != "0": ref["name"] = v; save_ua(ua); console.print("  [#5fd7af]✓[/#5fd7af]")
      elif ch == "2":
        new_role = self._pick_role_menu()
        if new_role: ref["role_id"] = new_role["id"]; save_ua(ua); console.print(f"  [#5fd7af]✓ Роль → {escape(new_role['id'])}[/#5fd7af]")
      elif ch == "3":
        result = _pick_provider_and_model(ctx)
        if result == "cancel": continue
        if result is None:
          ref["model"] = None; ref["provider"] = None; ref["api_key"] = None
          save_ua(ua); console.print("  [#5fd7af]✓ Авто (глобальный ключ)[/#5fd7af]")
        else:
          ref["model"] = result["model"]; ref["provider"] = result["provider"]; ref["api_key"] = result["key"]
          save_ua(ua)
          lbl = _get_model_label(result["model"]) if result["model"] else "авто"
          console.print(f"  [#5fd7af]✓ {escape(lbl)}  [{escape(result['provider'])}][/#5fd7af]")
      elif ch == "4":
        console.print("  [dim]Доп. инструкции (пустая строка = сохранить):[/dim]")
        lines_in: list[str] = []
        while True:
          ln = _pick("  > ")
          if ln == "": break
          lines_in.append(ln)
        ref["custom_prompt"] = "\n".join(lines_in) if lines_in else None
        save_ua(ua); console.print("  [#5fd7af]✓[/#5fd7af]")
      elif ch == "5":
        ref["active"] = not active; save_ua(ua)
        _, ns = _status_text(ref["active"])
        console.print(f"  [#5fd7af]✓ Статус → {ns}[/#5fd7af]")
      elif ch.lower() == "d":
        console.print(f"  [dim #ff5f5f]Удалить {escape(aid)}? (y/n):[/dim #ff5f5f]")
        if _pick("  > ").lower() == "y":
          ua["agents"] = [a for a in ua["agents"] if a.get("id") != aid]
          save_ua(ua); console.print("  [#5fd7af]✓ Удалён[/#5fd7af]"); return

  # ── Create agent ──────────────────────────────────────────────

  def _create_agent(self, ctx: CommandContext) -> None:
    console.print()
    console.print("  [bold white]Новый агент[/bold white]")
    console.print()
    role = self._pick_role_menu()
    if not role: return
    console.print()
    default_name = role.get("name", role["id"])
    console.print(f"  [dim]Имя агента (Enter = «{escape(default_name)}»):[/dim]")
    name_in = _pick("  > ")
    if name_in == "0": return
    name = name_in.strip() or default_name
    console.print()
    console.print("  [dim]Хочешь настроить провайдер + модель? [bold]y[/bold] / n (авто)[/dim]")
    chosen_provider: str | None = None
    chosen_key: str | None = None
    chosen_model: str | None = None
    if _pick("  > ").lower() == "y":
      result = _pick_provider_and_model(ctx)
      if result and result != "cancel":
        chosen_provider = result["provider"]
        chosen_key = result["key"]
        chosen_model = result["model"]
    ua = load_ua()
    new_id = _next_agent_id(ua)
    ua.setdefault("agents", []).append({
      "id": new_id,
      "name": name,
      "role_id": role["id"],
      "provider": chosen_provider,
      "api_key": chosen_key,
      "model": chosen_model,
      "active": True,
      "custom_prompt": None,
    })
    save_ua(ua)

    # §18.4 — register tab slot so Ctrl+N switches to this agent
    try:
      from ..ui.prompt import register_tab as _reg_tab
      _slot_num = int(new_id.split("-")[-1]) + 1  # agent-1 → slot 2, agent-2 → slot 3…
      if 1 <= _slot_num <= 9:
          _reg_tab(_slot_num, new_id)
    except Exception:
      pass

    console.print()
    _sep()
    t = Text("  ")
    t.append("✓ ", style="bold #5fd7af")
    t.append(f"{new_id}", style="bold cyan")
    t.append(f"  ·  {name}", style="white")
    t.append("  [active]", style="dim #5fd7af")
    if chosen_provider: t.append(f"  {chosen_provider}", style="dim #555555")
    console.print(t)
    console.print("  [dim #888888]Агент виден главному агенту и помощникам[/dim #888888]")
    console.print("  [dim #555555]Используй Ctrl+N для переключения на вкладку агента[/dim #555555]")
    _sep()
    console.print()

    # ── Role picker ───────────────────────────────────────────────

  def _pick_role_menu(self) -> dict | None:
    roles = load_roles()
    if not roles: console.print("  [red]Библиотека ролей не найдена[/red]"); return None
    page_size = 15
    page = 0
    total_pages = (len(roles) - 1) // page_size + 1
    while True:
      start = page * page_size
      end = min(start + page_size, len(roles))
      page_roles = roles[start:end]
      console.print()
      console.print(f"  [bold white]Выбери роль[/bold white]  [dim #555555]стр. {page+1}/{total_pages}[/dim #555555]")
      console.print()
      _sep()
      for i, role in enumerate(page_roles, start + 1):
        rid  = role.get("id", "")
        rname = role.get("name", "")
        rdesc = role.get("description", "")
        rtags = role.get("tags", [])
        tag_s = "  ".join(_pill(t) for t in rtags[:2])
        console.print(f"  [dim #666666]{i:>2}.[/dim #666666]  [cyan]{escape(rid):<24}[/cyan] [dim]{escape(rname)}[/dim]")
        if rdesc: console.print(f"        [dim #555555]{escape(rdesc[:70])}[/dim #555555]")
        if tag_s: console.print(f"        {tag_s}")
        console.print()
      _sep()
      nav = []
      if page > 0: nav.append("[dim]p — пред.[/dim]")
      if page < total_pages - 1: nav.append("[dim]n — след.[/dim]")
      nav.append("[dim]0 — отмена[/dim]")
      console.print("  " + "  ·  ".join(nav))
      console.print()
      ch = _pick()
      if ch in ("0", ""): return None
      if ch.lower() == "n" and page < total_pages - 1: page += 1; continue
      if ch.lower() == "p" and page > 0: page -= 1; continue
      if ch.isdigit():
        idx = int(ch) - 1
        if 0 <= idx < len(roles): return roles[idx]
      console.print("  [red]Неверный ввод[/red]")

    # ── Copy agent ────────────────────────────────────────────────

    def _copy_agent(self, agent: dict, ctx: CommandContext) -> None:
      ua = load_ua()
      new_id = _next_agent_id(ua)
      import copy
      clone = copy.deepcopy(agent)
      clone["id"] = new_id
      clone["name"] = agent.get("name", new_id) + " (копия)"
      clone["active"] = True
      ua.setdefault("agents", []).append(clone)
      save_ua(ua)
      console.print()
      console.print(f"  [#5fd7af]✓ Клон создан:[/] [cyan]{new_id}[/cyan]  ·  {escape(clone['name'])}")

    # ── Test / ping agent ─────────────────────────────────────────

    def _test_agent(self, agent: dict, ctx: CommandContext) -> None:
      import time
      aid = agent.get("id", "?")
      role_id = agent.get("role_id", "")
      model_id = agent.get("model") or ctx.config.get("model")
      prov = agent.get("provider", "")
      console.print()
      console.print(f"  [dim]Тестирую {escape(aid)} ({escape(role_id)}) → {escape(str(model_id))}[/dim]")
      console.print()
      t0 = time.time()
      try:
        from ..agent.sub_agent import call_sub_agent
        result = call_sub_agent(
          agent=agent,
          user_msg="Ответь одним словом: «работаю»",
          ctx=ctx,
          max_tokens=20,
        )
        elapsed = time.time() - t0
        console.print(f"  [#5fd7af]✓ Ответ за {elapsed:.1f}с:[/] {escape(str(result)[:80])}")
      except ImportError:
        # Заглушка если sub_agent не реализован
        elapsed = time.time() - t0
        console.print(f"  [dim #888888]sub_agent модуль не подключён — ping OK за {elapsed:.2f}с[/dim #888888]")
      except Exception as e:
        elapsed = time.time() - t0
        console.print(f"  [red]✗ Ошибка за {elapsed:.1f}с: {escape(str(e)[:120])}[/red]")

    # ── Capabilities matrix ───────────────────────────────────────

    def _matrix_view(self, ctx: CommandContext) -> None:
      from ..agent.agent_registry import AgentRegistry
      reg = AgentRegistry.get()
      matrix = reg.capabilities_matrix()
      if not matrix:
        console.print()
        console.print("  [dim #888888]models_capabilities.json не найден[/dim #888888]")
        return
      console.print()
      console.print("  [bold white]Матрица возможностей моделей[/bold white]")
      console.print()
      caps_cols = ["vision", "image_gen", "audio_in", "audio_out", "web_search"]
      header_cells = ["  " + f"{'Модель':<28}"] + [f"{c[:8]:^9}" for c in caps_cols] + [f"{'ctx_kb':^8}", f"{'tier':^8}"]
      from rich.text import Text as RText
      console.print("  " + "  ".join([
        f"[dim #666666]{'Модель':<28}[/dim #666666]",
        *[f"[dim #5fafff]{c[:8]:^9}[/dim #5fafff]" for c in caps_cols],
        "[dim #ffaf5f]ctx_kb [/dim #ffaf5f]",
        "[dim #af87ff]tier   [/dim #af87ff]",
      ]))
      console.print("  " + "─"*90)
      for entry in matrix:
        row_parts = [f"[cyan]{entry.model_id[:28]:<28}[/cyan]"]
        for cap in caps_cols:
          v = getattr(entry, cap, False)
          row_parts.append(f"[{'#5fd7af' if v else '#333333'}]{'✓' if v else '·':^9}[/]")
        row_parts.append(f"[#ffaf5f]{entry.context_kb:^8}[/#ffaf5f]")
        row_parts.append(f"[#af87ff]{entry.cost_tier:^8}[/#af87ff]")
        console.print("  " + "  ".join(row_parts))
      console.print()
      _pick("  Enter для выхода → ")

    # ── Peer / main agents view ────────────────────────────────────

    def _peer_view(self, ctx: CommandContext) -> None:
      ua = load_ua()
      peers = ua.get("peers", [])
      console.print()
      console.print("  [bold white]Пир-агенты (peer mains)[/bold white]")
      console.print()
      if not peers:
        console.print("  [dim #888888]Пир-агентов нет. Добавь через конфиг user_agents.json[/dim #888888]")
        console.print()
        _pick("  Enter → ")
        return
      _sep()
      for i, peer in enumerate(peers, 1):
        pid  = peer.get("id", f"peer-{i}")
        name = peer.get("name", pid)
        model = _get_model_label(peer.get("model"))
        active = peer.get("active", True)
        sc, ss = _status_text(active)
        console.print(f"  [dim #666666]{i}.[/dim #666666]  [bold magenta]{escape(pid)}[/bold magenta]  ·  {escape(name)}")
        console.print(f"      [{sc}]{ss}[/{sc}]  [dim #ff8c00]{escape(model)}[/dim #ff8c00]")
        endpoint = peer.get("endpoint")
        if endpoint: console.print(f"      [dim #444444]{escape(endpoint[:60])}[/dim #444444]")
        console.print()
      _sep()
      _pick("  Enter → ")

    # ── Batch enable / disable ────────────────────────────────────

    def _batch_action(self, ctx: CommandContext) -> None:
      ua = load_ua()
      agents = ua.get("agents", [])
      if not agents:
        console.print("  [dim]Нет sub-агентов[/dim]")
        return
      console.print()
      console.print("  [bold white]Групповое действие[/bold white]")
      console.print()
      console.print("  [dim #666666]1.[/dim #666666]  Включить всех")
      console.print("  [dim #666666]2.[/dim #666666]  Отключить всех")
      console.print("  [dim #666666]3.[/dim #666666]  Включить по тегу роли")
      console.print("  [dim #666666]4.[/dim #666666]  Отключить по тегу роли")
      console.print()
      console.print("  [dim #444444]0  назад[/dim #444444]")
      console.print()
      ch = _pick()
      if ch == "1":
        for a in agents: a["active"] = True
        save_ua(ua)
        console.print(f"  [#5fd7af]✓ Все {len(agents)} агентов включены[/#5fd7af]")
      elif ch == "2":
        for a in agents: a["active"] = False
        save_ua(ua)
        console.print(f"  [#5fd7af]✓ Все {len(agents)} агентов отключены[/#5fd7af]")
      elif ch in ("3", "4"):
        enable = (ch == "3")
        console.print("  [dim]Тег (напр. code, search, review):[/dim]")
        tag = _pick("  > ").strip().lower()
        if not tag: return
        roles = load_roles()
        role_ids_with_tag = {r["id"] for r in roles if tag in [t.lower() for t in r.get("tags", [])]}
        count = 0
        for a in agents:
          if a.get("role_id") in role_ids_with_tag:
            a["active"] = enable
            count += 1
        save_ua(ua)
        action = "включены" if enable else "отключены"
        console.print(f"  [#5fd7af]✓ {count} агентов {action} (тег «{escape(tag)}»)[/#5fd7af]")
  