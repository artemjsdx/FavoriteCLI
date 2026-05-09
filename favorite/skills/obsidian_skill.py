"""
favorite/skills/obsidian_skill.py — Obsidian vault integration skill (§41.4).
Allows agent to read/write Obsidian notes in a configured vault.
"""
import json
from pathlib import Path
from .base import ISkill

_OBSIDIAN_CONFIG = Path(__file__).resolve().parent.parent.parent / "config" / "obsidian.json"


def _load_vault_path() -> str | None:
    if _OBSIDIAN_CONFIG.exists():
        try:
            data = json.loads(_OBSIDIAN_CONFIG.read_text(encoding="utf-8"))
            return data.get("vault_path")
        except Exception:
            pass
    return None


class ObsidianSkill(ISkill):
    name = "obsidian"
    description = "Read and write Obsidian vault notes (§41.4)."
    _prompt_snippet = (
        "Skill: obsidian — чтение и запись заметок Obsidian vault.\n"
        "Usage:\n"
        "  <SKILL:name=obsidian>read:Daily/2026-05-05.md</SKILL>\n"
        "  <SKILL:name=obsidian>write:path=Daily/test.md:content=# Test</SKILL>\n"
        "  <SKILL:name=obsidian>list:Daily</SKILL>"
    )

    def get_prompt_snippet(self) -> str:
        return self._prompt_snippet

    def run(self, args: str, ctx=None, cfg=None) -> str:
        args = (args or "").strip()
        vault_path = _load_vault_path()
        if not vault_path:
            return (
                "[obsidian: vault не настроен.\n"
                "Укажи путь в config/obsidian.json:\n"
                '  {"vault_path": "/storage/emulated/0/Obsidian/MyVault"}]'
            )
        vault = Path(vault_path).expanduser()
        if not vault.exists():
            return f"[obsidian ERROR: vault не найден: {vault_path}]"

        parts = args.split(":", 1)
        cmd = parts[0].strip().lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "list":
            dir_path = vault / rest if rest else vault
            if not dir_path.exists():
                return f"[obsidian list: папка не найдена: {rest}]"
            notes = sorted(dir_path.glob("**/*.md"))[:50]
            lines = [str(n.relative_to(vault)) for n in notes]
            return f"[obsidian list: {len(lines)} заметок]\n" + "\n".join(lines)

        elif cmd == "read":
            note_path = vault / rest
            if not note_path.exists():
                return f"[obsidian read: заметка не найдена: {rest}]"
            content = note_path.read_text(encoding="utf-8", errors="replace")
            if len(content) > 6000:
                content = content[:6000] + "\n...[обрезано]"
            return f"[obsidian note: {rest}]\n{content}"

        elif cmd == "write":
            # write:path=X:content=Y
            import re
            m = re.match(r"path=([^:]+):content=(.*)", rest, re.S)
            if not m:
                return f"[obsidian write: формат — write:path=folder/note.md:content=текст]"
            note_rel = m.group(1).strip()
            note_content = m.group(2)
            note_path = vault / note_rel
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(note_content, encoding="utf-8")
            return f"[obsidian write: ✓ {note_rel} ({len(note_content)} символов)]"

        elif cmd == "append":
            note_path = vault / rest.split(":")[0].strip() if rest else None
            if not note_path:
                return "[obsidian append: путь не указан]"
            append_content = rest.split(":", 1)[1].strip() if ":" in rest else ""
            with open(note_path, "a", encoding="utf-8") as f:
                f.write("\n" + append_content)
            return f"[obsidian append: ✓ дописано в {rest.split(':')[0]}]"

        elif cmd == "search":
            query = rest.lower()
            matches = []
            for note in vault.rglob("*.md"):
                try:
                    text = note.read_text(encoding="utf-8", errors="replace").lower()
                    if query in text:
                        matches.append(str(note.relative_to(vault)))
                except Exception:
                    pass
            return f"[obsidian search: {len(matches)} совпадений]\n" + "\n".join(matches[:20])

        return f"[obsidian: неизвестная команда '{cmd}'. Доступно: list | read | write | append | search]"
