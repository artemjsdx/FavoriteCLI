"""
favorite/skills/markitdown_skill.py
Markitdown skill — converts documents (PDF, DOCX, HTML) to Markdown using markitdown lib.
"""
from pathlib import Path
from .base import ISkill


class MarkitdownSkill(ISkill):
    name = "markitdown"
    description = "Convert documents (PDF, DOCX, HTML, PPTX) to Markdown text."
    _prompt_snippet = (
        "Skill: markitdown — конвертирует документы (PDF, DOCX, HTML) в Markdown.\n"
        "Usage: <SKILL:name=markitdown>path: /tmp/document.pdf</SKILL>"
    )

    def get_prompt_snippet(self) -> str:
        return self._prompt_snippet

    def run(self, args: str, ctx=None, cfg=None) -> str:
        args = (args or "").strip()
        path_str = args.replace("path:", "").strip()
        if not path_str:
            return "[markitdown ERROR: path не указан]"
        p = Path(path_str).expanduser().resolve()
        if not p.exists():
            return f"[markitdown ERROR: файл не найден: {path_str}]"
        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(str(p))
            text = result.text_content or ""
            if len(text) > 8000:
                text = text[:8000] + "\n...[обрезано]"
            return f"[markitdown: {p.name}]\n{text}"
        except ImportError:
            return "[markitdown: библиотека не установлена. Запусти: pip install markitdown]"
        except Exception as e:
            return f"[markitdown ERROR: {e}]"
