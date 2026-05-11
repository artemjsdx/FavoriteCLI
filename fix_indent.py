import os, textwrap
from pathlib import Path

ROOT = Path("/storage/emulated/0/Цхранилище/Project/FavoriteCLI")

files = [
    ROOT / "favorite/skills/device_ctrl/config.py",
    ROOT / "favorite/skills/device_ctrl/adb_client.py",
    ROOT / "favorite/skills/device_ctrl/ui_dump.py",
    ROOT / "favorite/skills/device_ctrl/vision.py",
    ROOT / "favorite/skills/device_ctrl/cli_ui.py",
    ROOT / "favorite/skills/device_ctrl/tags.py",
    ROOT / "favorite/skills/device_ctrl/__init__.py",
    ROOT / "favorite/skills/__init__.py",
    ROOT / "favorite/commands/device_cmd.py",
]

for f in files:
    text = f.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    # Find minimum leading spaces (ignore blank lines)
    min_indent = 999
    for line in lines:
        stripped = line.lstrip(" ")
        if stripped.strip():  # non-empty line
            spaces = len(line) - len(stripped)
            if spaces < min_indent:
                min_indent = spaces
    if min_indent > 0:
        fixed = "".join(line[min_indent:] if line.startswith(" " * min_indent) else line for line in lines)
        f.write_text(fixed, encoding="utf-8")
        print(f"FIXED {f.name}: removed {min_indent} leading spaces")
    else:
        print(f"OK    {f.name}: no fix needed")