"""
favorite/skills/auto_context_skill.py
Auto-context skill — finds and injects relevant file snippets based on keywords.
"""
import re
import json
from pathlib import Path
from ..skills.base import ISkill


class AutoContextSkill(ISkill):
    name = "auto_context"
    description = "Automatically finds and injects relevant code snippets based on user query."
    _prompt_snippet = (
        "Skill: auto_context — автоматически находит файлы по ключевым словам.\n"
        "Usage: <SKILL:name=auto_context>keyword1 keyword2</SKILL>"
    )
    MAX_SNIPPET_CHARS = 500
    MAX_FILES = 5

    def get_prompt_snippet(self) -> str:
        return self._prompt_snippet

    def run(self, args: str, ctx=None, cfg=None) -> str:
        query = (args or "").strip()
        if not query or ctx is None:
            return "[auto_context: нет запроса или контекста]"
        workdir = Path(ctx.workdir)
        keywords = re.findall(r"\w+", query.lower())
        if not keywords:
            return "[auto_context: ключевые слова не найдены]"

        _IGNORE = {"__pycache__", "node_modules", ".git", "sessions", ".fav_snapshots",
                   ".venv", "venv", "dist", "build"}
        _CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml",
                      ".yml", ".toml", ".md", ".txt", ".sh"}

        def _score(path: Path) -> int:
            rel = str(path.relative_to(workdir)).lower()
            score = sum(3 for kw in keywords if kw in rel)
            try:
                text = path.read_text(encoding="utf-8", errors="replace").lower()
                score += sum(text.count(kw) for kw in keywords)
            except Exception:
                pass
            return score

        candidates = []
        try:
            for p in workdir.rglob("*"):
                if not p.is_file() or p.suffix not in _CODE_EXTS:
                    continue
                if any(ig in p.parts for ig in _IGNORE):
                    continue
                if len(p.relative_to(workdir).parts) > 5:
                    continue
                s = _score(p)
                if s > 0:
                    candidates.append((s, p))
        except Exception as e:
            return f"[auto_context ERROR: {e}]"

        candidates.sort(key=lambda x: -x[0])
        top = candidates[:self.MAX_FILES]
        if not top:
            return "[auto_context: не найдено релевантных файлов]"

        parts = [f'<auto_context query="{json.dumps(query)}">']
        for score, fpath in top:
            rel = str(fpath.relative_to(workdir))
            try:
                snippet = fpath.read_text(encoding="utf-8", errors="replace")[:self.MAX_SNIPPET_CHARS]
                if len(snippet) == self.MAX_SNIPPET_CHARS:
                    snippet += "\n...[обрезано]"
            except Exception:
                snippet = "(ошибка чтения)"
            parts.append(f'  <file path="{rel}" score="{score}">')
            parts.append(snippet)
            parts.append("  </file>")
        parts.append("</auto_context>")
        return "\n".join(parts)
