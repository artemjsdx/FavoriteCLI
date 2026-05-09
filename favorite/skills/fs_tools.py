"""
favorite/skills/fs_tools.py — Filesystem tools skill.
Reads and writes files within WORKDIR.
"""
import json
from pathlib import Path
from .base import ISkill


class FsToolsSkill(ISkill):
    @property
    def name(self) -> str:
        return "fs_tools"

    def run(self, args: str, ctx=None, cfg=None) -> str:
        """
        args format:
          read:path=relative/file.txt
          write:path=relative/file.txt:content=...
          append:path=relative/file.txt:content=...
          list:path=relative/dir
          exists:path=relative/file.txt
          delete:path=relative/file.txt
        """
        args = (args or "").strip()
        if not args:
            return "[fs_tools: нет команды. Используй: read:path=... | write:path=...:content=... | list:path=...]"

        workdir = Path(getattr(ctx, "workdir", ".")) if ctx else Path(".")

        # Parse command and params
        parts = args.split(":", 1)
        cmd = parts[0].strip().lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        def _parse_kv(s: str) -> dict:
            result: dict[str, str] = {}
            import re
            for m in re.finditer(r"(\w+)=([^:]*)", s):
                result[m.group(1)] = m.group(2).strip()
            return result

        kv = _parse_kv(rest)
        path_rel = kv.get("path", "").lstrip("/")
        content = kv.get("content", "")
        # Handle multi-line content — content= may span whole rest
        if cmd in ("write", "append") and "content=" in rest:
            # Extract everything after "content="
            ci = rest.find("content=")
            if ci != -1:
                content = rest[ci + 8:]

        # Safety: disallow paths outside workdir
        def _safe(p: str):
            full = (workdir / p).resolve()
            if not str(full).startswith(str(workdir.resolve())):
                raise PermissionError(f"Путь '{p}' выходит за пределы WORKDIR")
            return full

        if cmd == "read":
            if not path_rel:
                return "[fs_tools read: path не указан]"
            try:
                full = _safe(path_rel)
                if not full.exists():
                    return f"[fs_tools read: файл не найден: {path_rel}]"
                text = full.read_text(encoding="utf-8", errors="replace")
                if len(text) > 6000:
                    text = text[:6000] + "\n...[обрезано, показано 6000 символов]"
                return f"[file: {path_rel}]\n{text}"
            except Exception as e:
                return f"[fs_tools read ERROR: {e}]"

        elif cmd == "write":
            if not path_rel:
                return "[fs_tools write: path не указан]"
            try:
                full = _safe(path_rel)
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_text(content, encoding="utf-8")
                return f"[fs_tools write: {path_rel} записан ({len(content)} символов)]"
            except Exception as e:
                return f"[fs_tools write ERROR: {e}]"

        elif cmd == "append":
            if not path_rel:
                return "[fs_tools append: path не указан]"
            try:
                full = _safe(path_rel)
                full.parent.mkdir(parents=True, exist_ok=True)
                with open(full, "a", encoding="utf-8") as f:
                    f.write(content)
                return f"[fs_tools append: {path_rel} ({len(content)} символов добавлено)]"
            except Exception as e:
                return f"[fs_tools append ERROR: {e}]"

        elif cmd == "list":
            dir_rel = path_rel or "."
            try:
                full = _safe(dir_rel)
                if not full.exists():
                    return f"[fs_tools list: папка не найдена: {dir_rel}]"
                if not full.is_dir():
                    return f"[fs_tools list: не папка: {dir_rel}]"
                entries = sorted(full.iterdir(), key=lambda e: (e.is_file(), e.name))
                lines = []
                for e in entries[:50]:
                    mark = "/" if e.is_dir() else ""
                    lines.append(f"  {e.name}{mark}")
                result = "\n".join(lines)
                return f"[ls {dir_rel}]\n{result}"
            except Exception as e:
                return f"[fs_tools list ERROR: {e}]"

        elif cmd == "exists":
            if not path_rel:
                return "[fs_tools exists: path не указан]"
            try:
                full = _safe(path_rel)
                return f"[fs_tools exists: {path_rel} = {'true' if full.exists() else 'false'}]"
            except Exception as e:
                return f"[fs_tools exists ERROR: {e}]"

        elif cmd == "delete":
            if not path_rel:
                return "[fs_tools delete: path не указан]"
            try:
                full = _safe(path_rel)
                if not full.exists():
                    return f"[fs_tools delete: файл не найден: {path_rel}]"
                full.unlink()
                return f"[fs_tools delete: {path_rel} удалён]"
            except Exception as e:
                return f"[fs_tools delete ERROR: {e}]"

        return f"[fs_tools: неизвестная команда '{cmd}'. Доступно: read | write | append | list | exists | delete]"
