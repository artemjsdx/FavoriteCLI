from __future__ import annotations

from .base import ICommand, CommandContext


class PlanCommand(ICommand):
    name = "/plan"
    description = "Вкл/выкл режим планирования"
    priority = 9

    def execute(self, args: str, ctx: CommandContext) -> None:
        ctx.plan_mode = not getattr(ctx, "plan_mode", False)
