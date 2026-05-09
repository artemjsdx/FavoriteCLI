from .base import ICommand


class CommandRegistry:
  def __init__(self):
      self._commands: dict[str, ICommand] = {}

  def register(self, cmd: ICommand) -> None:
      self._commands[cmd.name.lower()] = cmd

  def get(self, name: str) -> ICommand | None:
      return self._commands.get(name.lower().strip())

  def all_sorted(self) -> list[ICommand]:
      return sorted(self._commands.values(), key=lambda c: c.priority)
