from pathlib import Path
from rich.table import Table
from rich.console import Console
from .base import ICommand, CommandContext
from ..tasks.manager import TaskManager

class TasksCommand(ICommand):
  name = "/tasks"
  description = "Управление задачами сессии"
  priority = 10

  def execute(self, args: str, ctx: CommandContext) -> None:
    console = Console()
    session_dir = Path(__file__).resolve().parent.parent.parent / "sessions" / ctx.session_id
    manager = TaskManager(session_dir)
  
    parts = args.split(maxsplit=1)
    subcommand = parts[0].lower() if parts else "list"
    subargs = parts[1] if len(parts) > 1 else ""
  
    if subcommand == "list":
        self._list_tasks(manager, console)
    elif subcommand == "add":
        if not subargs:
            console.print("[red]Укажите название задачи: /tasks add <название>[/red]")
            return
        task = manager.add_task(subargs)
        console.print(f"[green]Задача добавлена: {task.title} (ID: {task.id})[/green]")
    elif subcommand == "done":
        if not subargs:
            console.print("[red]Укажите ID задачи: /tasks done <id>[/red]")
            return
        task = manager.update_task(subargs, status="done")
        if task:
            console.print(f"[green]Задача выполнена: {task.title}[/green]")
        else:
            console.print(f"[red]Задача с ID {subargs} не найдена[/red]")
    elif subcommand == "todo":
        if not subargs:
            console.print("[red]Укажите ID задачи: /tasks todo <id>[/red]")
            return
        task = manager.update_task(subargs, status="todo")
        if task:
            console.print(f"[green]Задача возвращена в ToDo: {task.title}[/green]")
        else:
            console.print(f"[red]Задача с ID {subargs} не найдена[/red]")
    elif subcommand == "progress":
        if not subargs:
            console.print("[red]Укажите ID задачи: /tasks progress <id>[/red]")
            return
        task = manager.update_task(subargs, status="in_progress")
        if task:
            console.print(f"[green]Задача в процессе: {task.title}[/green]")
        else:
            console.print(f"[red]Задача с ID {subargs} не найдена[/red]")
    elif subcommand == "del":
        if not subargs:
            console.print("[red]Укажите ID задачи: /tasks del <id>[/red]")
            return
        if manager.delete_task(subargs):
            console.print(f"[green]Задача {subargs} удалена[/green]")
        else:
            console.print(f"[red]Задача с ID {subargs} не найдена[/red]")
    else:
        console.print(f"[red]Неизвестная подкоманда: {subcommand}[/red]")
        console.print("Доступные команды: list, add, done, todo, progress, del")

  def _list_tasks(self, manager: TaskManager, console: Console) -> None:
    tasks = manager.list_tasks()
    if not tasks:
        console.print("[dim]Список задач пуст[/dim]")
        return
  
    table = Table(title="Задачи сессии", show_header=True, header_style="bold #ff8c00")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Статус", width=15)
    table.add_column("Задача")
  
    # todo=dim, in_progress=orange, done=green, delegated=blue
    status_colors = {
        "todo": "dim",
        "in_progress": "bold #ffa500",
        "done": "green",
        "delegated": "blue",
    }
  
    for t in tasks:
        color = status_colors.get(t.status, "white")
        table.add_row(
            t.id,
            f"[{color}]{t.status}[/{color}]",
            t.title
        )
  
    console.print(table)
  