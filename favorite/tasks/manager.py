import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict

class Task:
  def __init__(
      self,
      title: str,
      id: Optional[str] = None,
      status: str = "todo",
      created_at: Optional[str] = None,
      updated_at: Optional[str] = None,
      notes: str = ""
  ):
      self.id = id or str(uuid.uuid4())[:8]
      self.title = title
      self.status = status
      self.created_at = created_at or datetime.now(timezone.utc).isoformat()
      self.updated_at = updated_at or self.created_at
      self.notes = notes

  def to_dict(self) -> Dict:
    return {
        "id": self.id,
        "title": self.title,
        "status": self.status,
        "created_at": self.created_at,
        "updated_at": self.updated_at,
        "notes": self.notes,
    }
  
  @classmethod
  def from_dict(cls, data: Dict) -> "Task":
    return cls(
        id=data.get("id"),
        title=data.get("title", ""),
        status=data.get("status", "todo"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        notes=data.get("notes", ""),
    )

class TaskManager:
  def __init__(self, session_dir: Path):
      self.session_dir = session_dir
      self.tasks_file = session_dir / "tasks.json"

  def _load_tasks(self) -> List[Task]:
      if not self.tasks_file.exists():
          return []
      try:
          data = json.loads(self.tasks_file.read_text(encoding="utf-8"))
          return [Task.from_dict(t) for t in data]
      except Exception:
          return []

  def _save_tasks(self, tasks: List[Task]) -> None:
      data = [t.to_dict() for t in tasks]
      self.tasks_file.write_text(
          json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
      )

  def add_task(self, title: str, status: str = "todo", notes: str = "") -> Task:
      tasks = self._load_tasks()
      task = Task(title=title, status=status, notes=notes)
      tasks.append(task)
      self._save_tasks(tasks)
      return task

  def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
      tasks = self._load_tasks()
      for t in tasks:
          if t.id == task_id:
              for key, value in kwargs.items():
                  if hasattr(t, key):
                      setattr(t, key, value)
              t.updated_at = datetime.now(timezone.utc).isoformat()
              self._save_tasks(tasks)
              return t
      return None

  def list_tasks(self) -> List[Task]:
      return self._load_tasks()

  def get_task(self, task_id: str) -> Optional[Task]:
      tasks = self._load_tasks()
      for t in tasks:
          if t.id == task_id:
              return t
      return None

  def delete_task(self, task_id: str) -> bool:
      tasks = self._load_tasks()
      new_tasks = [t for t in tasks if t.id != task_id]
      if len(new_tasks) < len(tasks):
          self._save_tasks(new_tasks)
          return True
      return False
