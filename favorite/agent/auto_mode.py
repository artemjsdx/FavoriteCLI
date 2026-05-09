"""
favorite/agent/auto_mode.py — §19.1 Full autonomous loop.

Replaces the stub in auto_cmd.py with a real:
  agent → executor → NEXT? → next tick → … loop
with counters, live-status, WAIT_USER/WAIT_LOGS support,
cycle detection and configurable limits.
"""
from __future__ import annotations

import json
import time
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Callable

from rich.console import Console
from rich.markup import escape
from rich.text import Text
from rich.live import Live

console = Console()

_MSK = timezone(timedelta(hours=3))


class AutoLoopStats:
    """Live counters for the autonomous loop."""
    def __init__(self) -> None:
        self.step          = 0
        self.total_tokens  = 0
        self.started_at    = time.time()
        self.paused        = False
        self.stop_flag     = False
        self.last_response = ""

    @property
    def elapsed_sec(self) -> float:
        return time.time() - self.started_at

    @property
    def elapsed_str(self) -> str:
        s = int(self.elapsed_sec)
        if s < 60:   return f"{s}с"
        if s < 3600: return f"{s//60}м{s%60:02d}с"
        return f"{s//3600}ч{(s%3600)//60:02d}м"

    def status_line(self, mode_label: str = "") -> Text:
        t = Text()
        t.append(f"  /auto ", style="bold #ff8c00")
        if mode_label:
            t.append(f"[{mode_label}] ", style="dim #ff8c00")
        t.append(f"шаг {self.step}  ", style="#ff8c00")
        t.append(f"⏱ {self.elapsed_str}  ", style="dim")
        if self.total_tokens:
            t.append(f"~{self.total_tokens//1000}k tokens  ", style="dim")
        if self.paused:
            t.append("⏸ ПАУЗА", style="bold yellow")
        return t


class AutoLoop:
    """
    Main autonomous loop. Usage:

        loop = AutoLoop(
            send_to_agent=lambda msg: ...,   # returns (reply_text, tokens_used)
            execute_tags=lambda reply: ...,  # returns (results_text, wait_user_flag)
            cfg=cfg,
            workdir=workdir,
            session_id=session_id,
        )
        loop.run(initial_message="Начни работу над задачей X.")
    """

    def __init__(
        self,
        send_to_agent: Callable[[str], tuple[str, int]],
        execute_tags:  Callable[[str, object], tuple[str, bool]],
        cfg,
        workdir:    str,
        session_id: str,
        mode_label: str = "",
    ) -> None:
        self._send        = send_to_agent
        self._execute     = execute_tags
        self._cfg         = cfg
        self._workdir     = Path(workdir)
        self._session_id  = session_id
        self._mode_label  = mode_label
        self._stats       = AutoLoopStats()
        self._log_path    = self._workdir / "sessions" / session_id / "auto.log"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._modules     = self._load_modules()
        self._recent_hashes: list[int] = []

    def _load_modules(self) -> dict:
        f = self._workdir / "config" / "modules.json"
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _log(self, text: str) -> None:
        ts = datetime.now(_MSK).strftime("%H:%M:%S")
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[{ts}] {text}\n")

    def _detect_cycle(self, response: str) -> bool:
        if not self._modules.get("cycle_detection", True):
            return False
        threshold = self._modules.get("cycle_similarity_threshold_pct", 85) / 100.0
        h = hash(response[:200])
        count = sum(1 for rh in self._recent_hashes if rh == h)
        self._recent_hashes.append(h)
        if len(self._recent_hashes) > 20:
            self._recent_hashes.pop(0)
        if count >= 2:
            self._log(f"ЦИКЛ ОБНАРУЖЕН: step={self._stats.step}")
            return True
        return False

    def stop(self) -> None:
        self._stats.stop_flag = True

    def pause(self) -> None:
        self._stats.paused = True

    def resume(self) -> None:
        self._stats.paused = False

    @property
    def stats(self) -> AutoLoopStats:
        return self._stats

    def run(
        self,
        initial_message: str = "",
        max_steps:       int  = 100,
        max_duration_sec: int = 36000,
    ) -> str:
        """Execute the autonomous loop. Returns stop reason."""
        stats = self._stats
        msg = initial_message or "Продолжай работу."

        self._log(f"START: max_steps={max_steps}, max_duration={max_duration_sec}s")
        self._log(f"Initial message: {initial_message[:200]}")

        with Live(stats.status_line(self._mode_label), console=console,
                  refresh_per_second=4, transient=True) as live:

            while not stats.stop_flag:
                # — Pause —
                while stats.paused and not stats.stop_flag:
                    live.update(Text("  ⏸ /auto на паузе — нажми /auto resume", style="yellow"))
                    time.sleep(0.5)

                if stats.stop_flag:
                    break

                # — Limits —
                if stats.step >= max_steps:
                    self._log(f"STOP: max_steps={max_steps} reached")
                    return f"max_steps ({max_steps})"
                if stats.elapsed_sec >= max_duration_sec:
                    self._log(f"STOP: max_duration={max_duration_sec}s reached")
                    return f"max_duration ({max_duration_sec}s)"

                stats.step += 1
                live.update(stats.status_line(self._mode_label))
                self._log(f"STEP {stats.step}: sending to agent")

                # — Send to agent —
                try:
                    reply, tokens = self._send(msg)
                except Exception as e:
                    self._log(f"SEND ERROR: {e}")
                    console.print(f"  [red]/auto ошибка отправки:[/red] {escape(str(e))}")
                    time.sleep(3)
                    continue

                stats.total_tokens += tokens or 0
                stats.last_response = reply
                live.update(stats.status_line(self._mode_label))

                # — Cycle detection —
                if self._detect_cycle(reply):
                    console.print(
                        "  [bold yellow]⚠ Детектор циклов: агент зациклился. Инжектирую прерывание.[/bold yellow]"
                    )
                    self._log("CYCLE BREAK injected")
                    msg = ("[SYSTEM] Обнаружен цикл. Ты повторяешь одно и то же. "
                           "Сделай принципиально другой шаг или используй DONE.")
                    continue

                # — Execute tags —
                try:
                    results, wait_user = self._execute(reply, self._stats)
                except Exception as e:
                    self._log(f"EXECUTE ERROR: {e}")
                    results, wait_user = f"[EXECUTE ERROR] {e}", False

                # — WAIT_USER —
                if wait_user or "__WAIT_USER__" in (results or ""):
                    self._log("WAIT_USER: autonomy paused for human input")
                    console.print()
                    console.print("  [bold #ff8c00]⏸ /auto: агент ожидает тебя. Ответь, потом /auto resume[/bold #ff8c00]")
                    stats.paused = True
                    while stats.paused and not stats.stop_flag:
                        time.sleep(0.5)
                    if stats.stop_flag:
                        break
                    continue

                # — Check for NEXT tag —
                has_next = "[[NEXT]]" in reply or "<NEXT>" in reply or "[CONTINUE]" in (results or "")
                if not has_next and "DONE" not in reply and "[STOP]" not in reply:
                    # Continuity inspector: prod agent to continue
                    self._log(f"STEP {stats.step}: no NEXT found, injecting continuity prompt")
                    msg = (
                        f"[SYSTEM AUTO-CONTINUE] Шаг {stats.step} завершён. "
                        f"Продолжай выполнение задачи. Используй NEXT если хочешь ещё такт, "
                        f"или DONE если задача полностью завершена.\n"
                        f"[OUTPUT]\n{(results or '')[:2000]}"
                    )
                    continue

                if "DONE" in reply or "[STOP]" in reply:
                    self._log(f"STOP: DONE at step {stats.step}")
                    return "done"

                # Build next message
                msg = f"[SYSTEM] Шаг {stats.step} выполнен.\n[OUTPUT]\n{(results or '')[:3000]}"
                self._log(f"STEP {stats.step}: OK, tokens+={tokens}")

        self._log(f"STOPPED at step {stats.step}")
        return "stopped"
