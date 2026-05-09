from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandContext:
  workdir: str
  session_id: str
  platform: Any
  config: Any
  mgr: Any = None
  plan_mode: bool = False
  auto_mode: bool = False
  telegram: Any = None
  history: Any = field(default_factory=list)
  shell_cwd: str = ""  # tracks working dir across SHELL_RAW calls; starts empty = use workdir
  registry: Any = None  # CommandRegistry ref, injected in app.py


class ICommand(ABC):
  name: str
  description: str
  priority: int = 99

  @abstractmethod
  def execute(self, args: str, ctx: CommandContext) -> None:
      pass
