"""
favorite/skills/compaction_skill.py
Context compaction skill — summarizes long conversation history to save tokens.
"""
from pathlib import Path
import json
from datetime import datetime
from ..skills.base import ISkill


class CompactionSkill(ISkill):
    name = "compaction"
    description = "Compresses long conversation history into a compact summary to reduce token usage."
    _prompt_snippet = (
        "Skill: compaction — сжимает историю диалога до краткого саммари.\n"
        "Usage: <SKILL:name=compaction>max_messages=50</SKILL>"
    )

    def get_prompt_snippet(self) -> str:
        return self._prompt_snippet

    def run(self, args: str, ctx=None, cfg=None) -> str:
        if ctx is None:
            return "[compaction: нет контекста]"
        try:
            from ..agent.tags import extract_tags
            session_dir = Path(ctx.workdir) / "sessions" / ctx.session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            summary_path = session_dir / "context_summary.md"

            # Retrieve history
            history = getattr(ctx, "history", [])
            if len(history) < 10:
                return f"[compaction: слишком короткая история ({len(history)} сообщений), пропускаю]"

            # Build raw text from last 50 messages
            max_msgs = 50
            to_compact = history[-max_msgs:]
            raw = "\n\n".join(
                f"[{m.get('role','?').upper()}]\n{str(m.get('content',''))[:1000]}"
                for m in to_compact
            )

            # Build summary prompt
            summary_prompt = (
                "Ты аналитик. Создай максимально сжатое, но исчерпывающее резюме следующей истории диалога.\n"
                "Сохрани: главную цель, принятые решения, текущее состояние задачи, важные факты.\n"
                "Формат: Markdown, до 800 слов.\n\n"
                "История:\n" + raw
            )

            # Call LLM for summary
            try:
                from ..agent.llm import call_llm
                summary = call_llm(
                    system="You are a concise context summarizer.",
                    user=summary_prompt,
                    cfg=cfg,
                    model=None,
                )
            except Exception as e:
                summary = f"[Авто-саммари недоступно: {e}]\n\nПоследнее состояние:\n{raw[-2000:]}"

            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            header = f"<!-- context summary generated {ts}, {len(history)} messages compacted -->\n"
            summary_path.write_text(header + summary, encoding="utf-8")

            return (
                f"[compaction: сохранено резюме {len(summary)} символов → {summary_path}]\n"
                f"Текущий контекст сжат. История будет сброшена на {max(0, len(history)-max_msgs)} ранних сообщений."
            )
        except Exception as e:
            return f"[compaction ERROR: {e}]"
