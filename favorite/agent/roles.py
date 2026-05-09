from dataclasses import dataclass, field


@dataclass
class AgentRole:
  id: str
  name: str
  description: str
  system_prompt: str
  priority: int = 99
  tags: list[str] = field(default_factory=list)


@dataclass
class MainAgent:
  agent_id: str
  provider: str
  api_key: str
  model: str
  role: AgentRole | None = None
  active: bool = True


@dataclass
class SubAgent:
  agent_id: str
  provider: str
  api_key: str
  model: str
  role: AgentRole | None = None
  parent_id: str = "main-1"
  active: bool = True
