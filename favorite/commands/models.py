from .base import ICommand, CommandContext
from ..ui.chat import print_agent_message, print_separator
from ..ui.welcome import print_info


class ModelsCommand(ICommand):
  name = "/models"
  description = "Все модели всех провайдеров"
  priority = 3

  def execute(self, args: str, ctx: CommandContext) -> None:
    cfg = ctx.config
    print_separator()
    print_agent_message("Сводка по всем API и моделям", "system")
    print_info("  --- FavoriteAPI ---")
    for k in cfg.favorite_api_keys:
        masked = k["key"][:12] + "..."
        model = k.get("model") or "дефолтная"
        role = k.get("role") or "Не назначено"
        print_info(f"  {masked}  |  {model}  |  {role}")
    print_info("  --- OpenRouter ---")
    for k in cfg.openrouter_keys:
        masked = k["key"][:18] + "..."
        model = k.get("model") or "не выбрана"
        role = k.get("role") or "Не назначено"
        print_info(f"  {masked}  |  {model}  |  {role}")
    print_separator()
