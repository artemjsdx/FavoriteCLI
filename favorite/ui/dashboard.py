#!/usr/bin/env python3
"""
dashboard.py — Real-time observability для FavoriteCLI
Аудит и мониторинг сессий, токенов, команд в реальном времени
"""
import os
import sys
import json
import time
import signal
from pathlib import Path
from datetime import datetime
from collections import Counter
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich import box

console = Console()

class Dashboard:
    def __init__(self, sessions_dir: Path = None):
        self.sessions_dir = sessions_dir or Path("sessions")
        self.stats = Counter()
        self.running = True
        
        signal.signal(signal.SIGINT, self._handle_interrupt)
        
    def _handle_interrupt(self, signum, frame):
        self.running = False
        console.print("[red]Завершение...[/red]")
        
    def load_all_sessions(self) -> list[dict]:
        sessions = []
        if self.sessions_dir.exists():
            for session_id in sorted(self.sessions_dir.iterdir()):
                if session_id.is_dir():
                    meta_file = session_id / "meta.json"
                    if meta_file.exists():
                        try:
                            meta = json.loads(meta_file.read_text(encoding="utf-8"))
                            sessions.append(meta)
                        except Exception as e:
                            pass
        return sorted(sessions, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def count_files_by_pattern(self, directory: str, pattern: str) -> int:
        try:
            return sum(1 for _ in Path(directory).rglob(pattern))
        except:
            return 0
            
    def count_files_with_text(self, directory: str, text: str) -> int:
        count = 0
        try:
            for py_file in Path(directory).rglob("*.py"):
                if "favorite" in str(py_file):
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        if text in content:
                            count += 1
                    except:
                        pass
        except:
            pass
        return count
    
    def generate_report(self) -> dict:
        sessions = self.load_all_sessions()
        
        stats = {
            "total_sessions": len(sessions),
            "total_tokens": sum(s.get("stats", {}).get("total_tokens", 0) for s in sessions),
            "total_requests": sum(s.get("stats", {}).get("requests", 0) for s in sessions),
            "session_titles": Counter(),
            "avg_tokens_per_session": 0,
            "favorite_cli_stats": {},
        }
        
        for session in sessions:
            title = session.get("title", "no title")
            stats["session_titles"][title] += 1
            stats["total_tokens"] += session.get("stats", {}).get("total_tokens", 0)
            stats["total_requests"] += session.get("stats", {}).get("requests", 0)
            
        if sessions:
            stats["avg_tokens_per_session"] = stats["total_tokens"] / len(sessions) if sessions else 0
            
        stats["favorite_cli_stats"] = {
            "total_python_files": self.count_files_by_pattern("favorite", "*.py"),
            "files_with_subprocess": self.count_files_with_text("favorite", "subprocess"),
            "files_with_asyncio": self.count_files_with_text("favorite", "asyncio"),
            "files_with_threading": self.count_files_with_text("favorite", "threading"),
            "num_commands": len(list(Path("favorite/commands").glob("*.py"))),
        }
        
        return stats
    
    def render_single_table(self, title, columns, rows):
        table = Table(title=title, box=box.ROUNDED)
        for col in columns:
            table.add_column(col, style="green")
            
        for row in rows:
            formatted_row = [str(v) for v in row]
            table.add_row(*formatted_row)
        return table
    
    def create_live_dashboard(self):
        report = self.generate_report()
        
        table_data = []
        table_data.append(["Всего сессий", str(report["total_sessions"])])
        table_data.append(["Всего токенов (LLM)", str(report["total_tokens"])])
        table_data.append(["Всего запросов (LLM)", str(report["total_requests"])])
        table_data.append(["Средних токенов на сессию", f"{report['avg_tokens_per_session']:.2f}"])
        
        fs = report["favorite_cli_stats"]
        table_data.append(["Файлов Python в favorite/", str(fs["total_python_files"])])
        table_data.append(["Файлов с subprocess", str(fs["files_with_subprocess"])])
        table_data.append(["Файлов с asyncio", str(fs["files_with_asyncio"])])
        table_data.append(["Файлов с threading", str(fs["files_with_threading"])])
        table_data.append(["Количество команд", str(fs["num_commands"])])
        
        top_titles = report["session_titles"].most_common(5)
        if top_titles:
            table_data.append(["Наиболее частые заголовки сессий:"])
            for title, count in top_titles:
                table_data.append([f"  {title}: {count}"])
        else:
            table_data.append(["Нет данных по заголовкам"])
            
        return self.render_single_table("Dashboard - Real-time Monitor", ["Metric", "Value"], table_data)
    
    def start(self):
        console.print("[bold blue]Запуск Dashboard FavoriteCLI в режиме реального времени...[/bold blue]")
        console.print("[yellow]Нажми Ctrl+C для выхода[/yellow]")
        
        with Live(self.create_live_dashboard(), refresh_per_second=1) as live:
            while self.running:
                report = self.generate_report()
                live.update(self.create_live_dashboard())
                time.sleep(1)
                
        console.print("[green]Dashboard остановлен[/green]")
        
    def generate_text_report(self):
        report = self.generate_report()
        
        console.print("[bold]=== FAVORITECLI AUDIT ===[/bold]")
        console.print(f"Generated at: {datetime.now().isoformat()}")
        console.print("")
        
        console.print("[bold]СЕССИИ[/bold]")
        console.print(f"  Total sessions: {report['total_sessions']}")
        console.print(f"  Total tokens (LLM): {report['total_tokens']}")
        console.print(f"  Total requests (LLM): {report['total_requests']}")
        avg = report['avg_tokens_per_session']
        console.print(f"  Avg tokens per session: {avg:.2f}")
        
        top_titles = report['session_titles'].most_common(5)
        if top_titles:
            console.print(f"  Top 5 session titles:")
            for title, count in top_titles:
                console.print(f"    {title}: {count}")
                
        console.print("")
        console.print("[bold]КОДОВАЯ БАЗА FAVORITECLI[/bold]")
        fs = report['favorite_cli_stats']
        console.print(f"  Python files in favorite/: {fs['total_python_files']}")
        console.print(f"  Files with subprocess: {fs['files_with_subprocess']}")
        console.print(f"  Files with asyncio: {fs['files_with_asyncio']}")
        console.print(f"  Files with threading: {fs['files_with_threading']}")
        console.print(f"  Number of commands: {fs['num_commands']}")
        
        console.print("")
        console.print("[bold]ВЫВОДЫ[/bold]")
        
        if fs['files_with_asyncio'] < fs['files_with_subprocess']:
            pct = int(fs['files_with_asyncio'] / fs['files_with_subprocess'] * 100) if fs['files_with_subprocess'] else 0
            console.print(f"  Async code usage: ~{pct}% of files with subprocess")
        else:
            console.print("  Async code dominates")
            
        if report['total_sessions'] == 0:
            console.print("  No sessions in journal")
        else:
            console.print(f"  {report['total_sessions']} sessions analyzed")
            
        return report


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        dashboard = Dashboard()
        dashboard.start()
    else:
        dashboard = Dashboard()
        dashboard.generate_text_report()
