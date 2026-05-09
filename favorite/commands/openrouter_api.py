from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich import box

from .base import ICommand, CommandContext
from ..ui.chat import print_separator, print_status_line

console = Console()

_PROVIDER_NAMES: dict[str, str] = {
  "anthropic":             "Anthropic       (Claude)",
  "openai":                "OpenAI          (GPT)",
  "google":                "Google          (Gemini)",
  "deepseek":              "DeepSeek",
  "qwen":                  "Qwen            (Alibaba)",
  "meta-llama":            "Meta            (Llama)",
  "mistralai":             "Mistral",
  "x-ai":                  "xAI             (Grok)",
  "cohere":                "Cohere",
  "nvidia":                "NVIDIA",
  "perplexity":            "Perplexity",
  "microsoft":             "Microsoft       (Phi)",
  "amazon":                "Amazon          (Nova)",
  "nousresearch":          "Nous Research",
  "nous-research":         "Nous Research",
  "liquid":                "Liquid AI",
  "inflection":            "Inflection      (Pi)",
  "minimax":               "MiniMax",
  "baidu":                 "Baidu           (ERNIE)",
  "cognitivecomputations": "Dolphin AI",
  "inclusionai":           "Inclusion AI",
  "poolside":              "Poolside",
  "tencent":               "Tencent         (Hunyuan)",
  "z-ai":                  "Z.AI            (GLM)",
  "ai21":                  "AI21 Labs",
  "aion-labs":             "Aion Labs",
  "alfredpros":            "AlfredPros",
  "alibaba":               "Alibaba",
  "allenai":               "Allen AI",
  "alpindale":             "Alpindale",
  "anthracite-org":        "Anthracite",
  "arcee-ai":              "Arcee AI",
  "bytedance":             "ByteDance       (Doubao)",
  "bytedance-seed":        "ByteDance Seed",
  "databricks":            "Databricks",
  "deepcogito":            "DeepCogito",
  "essentialai":           "Essential AI",
  "gryphe":                "Gryphe",
  "ibm-granite":           "IBM Granite",
  "inception":             "Inception AI",
  "kwaipilot":             "Kwai Pilot",
  "mancer":                "Mancer",
  "moonshotai":            "Moonshot AI     (Kimi)",
  "morph":                 "Morph",
  "nex-agi":               "Nex AGI",
  "openrouter":            "OpenRouter      (Auto)",
  "prime-intellect":       "Prime Intellect",
  "rekaai":                "Reka AI",
  "relace":                "Relace",
  "sao10k":                "Sao10k",
  "stepfun":               "StepFun",
  "switchpoint":           "SwitchPoint",
  "thedrummer":            "TheDrummer",
  "tngtech":               "TNG Tech",
  "undi95":                "Undi95",
  "upstage":               "Upstage         (SOLAR)",
  "writer":                "Writer          (Palmyra)",
  "xiaomi":                "Xiaomi          (MiMo)",
  "groq":                  "Groq",
  "sophosympatheia":       "Sophosympatheia",
  "pygmalionai":           "PygmalionAI",
  "01-ai":                 "01.AI           (Yi)",
}


def _provider_label(prefix: str) -> str:
  return _PROVIDER_NAMES.get(prefix, prefix.replace("-", " ").title())


def _fmt_ctx(ctx_k: int) -> str:
  if ctx_k >= 1000:
      return f"{ctx_k // 1000}M"
  return f"{ctx_k}k" if ctx_k else ""


def _fmt_cost(cost: float) -> str:
  if cost == 0:
      return "FREE"
  per_m = cost * 1_000_000
  if per_m < 0.1:
      return "<$0.1/1M"
  if per_m < 10:
      return f"${per_m:.2f}/1M"
  return f"${per_m:.1f}/1M"


def _fetch_all_models(key_val: str) -> dict[str, list]:
  try:
      import requests
      r = requests.get(
          "https://openrouter.ai/api/v1/models",
          headers={"Authorization": f"Bearer {key_val}"},
          timeout=15,
      )
      if r.status_code != 200:
          return {}
      data = r.json().get("data", [])
      grouped: dict[str, list] = {}
      for m in data:
          mid = m["id"]
          prefix = mid.split("/")[0]
          if prefix.startswith("~"):
              continue
          p = m.get("pricing", {})
          try:
              cost = float(p.get("prompt", 0)) + float(p.get("completion", 0))
          except (TypeError, ValueError):
              cost = 999.0
          ctx_k = (m.get("context_length") or 0) // 1000
          grouped.setdefault(prefix, []).append((mid, ctx_k, cost))
      for prefix in grouped:
          grouped[prefix].sort(key=lambda x: x[2])
      return grouped
  except Exception:
      return {}


_CURATED_FALLBACK: dict[str, list] = {
  "google":    [("google/gemini-2.5-flash-preview:free", 1000, 0), ("google/gemini-2.5-pro-preview", 1000, 1)],
  "anthropic": [("anthropic/claude-sonnet-4", 200, 2), ("anthropic/claude-opus-4", 200, 5)],
  "openai":    [("openai/gpt-4o-mini", 128, 1), ("openai/gpt-4o", 128, 3)],
  "deepseek":  [("deepseek/deepseek-r1:free", 128, 0), ("deepseek/deepseek-chat-v3-0324", 64, 1)],
  "qwen":      [("qwen/qwen3-coder:free", 128, 0), ("qwen/qwen3-235b-a22b", 128, 2)],
  "meta-llama": [("meta-llama/llama-3.1-8b-instruct:free", 128, 0)],
  "mistralai": [("mistralai/mistral-7b-instruct:free", 32, 0)],
}


def _pick_model_menu(key_val: str) -> str:
  print_separator()
  print_status_line("Загрузка моделей", "openrouter.ai...", color="#ff8c00")
  grouped = _fetch_all_models(key_val) or _CURATED_FALLBACK

  def provider_sort(prefix: str):
      has_free = any(":free" in mid for mid, _, _ in grouped[prefix])
      return (0 if has_free else 1, _provider_label(prefix))

  providers = sorted(grouped.keys(), key=provider_sort)

  while True:
      table = Table(
          box=box.SIMPLE,
          show_header=True,
          header_style="bold #ff8c00",
          border_style="#333333",
          padding=(0, 1),
      )
      table.add_column("#", style="dim", width=4, justify="right")
      table.add_column("Провайдер", style="#cccccc", min_width=28)
      table.add_column("Мод.", justify="right", style="dim", width=5)
      table.add_column("Бесплатные", justify="left", width=16)

      free_section_done = False
      for i, prefix in enumerate(providers, 1):
          models = grouped[prefix]
          total = len(models)
          free_n = sum(1 for mid, _, _ in models if ":free" in mid)
          if not free_section_done and free_n == 0:
              table.add_row("", "[dim]──── платные ────[/dim]", "", "")
              free_section_done = True
          free_str = f"[green]✓ {free_n} бесплатных[/green]" if free_n else ""
          table.add_row(f"[dim]{i}[/dim]", _provider_label(prefix), str(total), free_str)

      table.add_row("", "[dim]──────────────────[/dim]", "", "")
      table.add_row(
          f"[dim]{len(providers) + 1}[/dim]",
          "[dim italic]Ввести ID вручную[/dim italic]",
          "", "",
      )

      print_separator()
      console.print("  [bold #ff8c00]Шаг 1[/bold #ff8c00] [dim]— выбери провайдера:[/dim]")
      console.print(table)
      print_separator()

      try:
          choice = input(f"  Провайдер [1-{len(providers) + 1}]: ").strip()
      except (EOFError, KeyboardInterrupt):
          return "qwen/qwen3-coder:free"

      if not choice.isdigit():
          continue
      back_n = len(providers) + 1
      idx = int(choice) - 1
      if int(choice) == back_n:
          try:
              m = input("  ID модели (напр. openai/gpt-4o): ").strip()
          except (EOFError, KeyboardInterrupt):
              m = ""
          return m or "qwen/qwen3-coder:free"
      if not (0 <= idx < len(providers)):
          console.print("  [red]Неверный номер.[/red]")
          continue

      prefix = providers[idx]
      models = grouped[prefix]
      label = _provider_label(prefix)

      model_table = Table(
          box=box.SIMPLE,
          show_header=True,
          header_style="bold #ff8c00",
          border_style="#333333",
          padding=(0, 1),
      )
      model_table.add_column("#", style="dim", width=4, justify="right")
      model_table.add_column("ID модели", style="#cccccc", min_width=42)
      model_table.add_column("Контекст", justify="right", width=9, style="dim")
      model_table.add_column("Цена", justify="right", width=12)

      for j, (mid, ctx, cost) in enumerate(models, 1):
          is_free = ":free" in mid
          cost_str = "[green bold]FREE[/green bold]" if is_free else f"[dim]{_fmt_cost(cost)}[/dim]"
          ctx_str = _fmt_ctx(ctx) if ctx else ""
          model_table.add_row(
              f"[dim]{j}[/dim]",
              f"[green]{mid}[/green]" if is_free else mid,
              ctx_str,
              cost_str,
          )
      back2 = len(models) + 1
      model_table.add_row(
          f"[dim]{back2}[/dim]",
          "[dim italic]← Назад к провайдерам[/dim italic]",
          "", "",
      )

      print_separator()
      console.print(f"  [bold #ff8c00]Шаг 2[/bold #ff8c00] [dim]— модели[/dim] [bold]{label}[/bold]:")
      console.print(model_table)
      print_separator()

      try:
          choice2 = input(f"  Модель [1-{back2}]: ").strip()
      except (EOFError, KeyboardInterrupt):
          continue

      if not choice2.isdigit():
          continue
      if int(choice2) == back2:
          continue
      midx = int(choice2) - 1
      if 0 <= midx < len(models):
          chosen = models[midx][0]
          console.print(f"  [green]Выбрано:[/green] [bold]{chosen}[/bold]")
          return chosen
      console.print("  [red]Неверный номер.[/red]")


class OpenRouterApiCommand(ICommand):
  name = "/OpenRouter API"
  description = "Управление ключами OpenRouter"
  priority = 2

  def execute(self, args: str, ctx: CommandContext) -> None:
      cfg = ctx.config
      while True:
          print_separator()
          console.print("  [bold #ff8c00]OpenRouter[/bold #ff8c00] [dim]— управление ключами[/dim]")
          keys = cfg.openrouter_keys
          if not keys:
              console.print("  [dim]Ключи не добавлены.[/dim]")
          else:
              for i, k in enumerate(keys, 1):
                  key_str = k["key"]
                  masked = key_str[:12] + "..." + key_str[-4:] if len(key_str) > 18 else "***"
                  model = k.get("model") or "[dim]не выбрана[/dim]"
                  role = k.get("role") or "—"
                  dflt = " [bold #ff8c00][дефолт][/bold #ff8c00]" if k.get("is_default") else ""
                  console.print(
                      f"  [dim][{i}][/dim]  [#888888]{masked}[/#888888]"
                      f"  [dim]|[/dim]  {model}"
                      f"  [dim]|[/dim]  [dim]роль: {role}[/dim]{dflt}"
                  )
          print_separator()
          console.print("  [dim][1][/dim] Добавить ключ")
          console.print("  [dim][2][/dim] Удалить ключ")
          console.print("  [dim][3][/dim] Сменить модель")
          console.print("  [dim][0][/dim] Назад")
          try:
              choice = input("  Выбери: ").strip()
          except (EOFError, KeyboardInterrupt):
              break

          if choice == "0":
              break

          elif choice == "1":
              try:
                  key_val = input("  Ключ (sk-or-v1-...): ").strip()
              except (EOFError, KeyboardInterrupt):
                  continue
              if not key_val:
                  console.print("  [dim]Пусто — отменено.[/dim]")
                  continue
              model = _pick_model_menu(key_val)
              cfg.add_openrouter_key(key_val, model=model)
              console.print(f"  [green]Ключ добавлен:[/green] {model}")

          elif choice == "2":
              if not keys:
                  console.print("  [dim]Нечего удалять.[/dim]")
                  continue
              try:
                  n = input("  Номер ключа для удаления: ").strip()
              except (EOFError, KeyboardInterrupt):
                  continue
              if n.isdigit() and cfg.remove_openrouter_key(int(n) - 1):
                  console.print("  [green]Удалён.[/green]")
              else:
                  console.print("  [red]Неверный номер.[/red]")

          elif choice == "3":
              if not keys:
                  console.print("  [dim]Нет ключей.[/dim]")
                  continue
              try:
                  n = input("  Номер ключа: ").strip()
              except (EOFError, KeyboardInterrupt):
                  continue
              if not n.isdigit() or not (0 <= int(n) - 1 < len(keys)):
                  console.print("  [red]Неверный номер.[/red]")
                  continue
              k = keys[int(n) - 1]
              model = _pick_model_menu(k["key"])
              if model and cfg.set_openrouter_model(int(n) - 1, model):
                  console.print(f"  [green]Модель обновлена:[/green] {model}")
