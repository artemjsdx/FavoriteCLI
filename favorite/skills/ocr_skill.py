"""
favorite/skills/ocr_skill.py
OCR skill — reads text from images via FavoriteChrome server or tesseract.
"""
import base64
from pathlib import Path
from .base import ISkill


class OcrSkill(ISkill):
    name = "ocr"
    description = "Extract text from images (OCR). Requires FavoriteChrome or tesseract."
    _prompt_snippet = (
        "Skill: ocr — извлекает текст с изображений.\n"
        "Usage: <SKILL:name=ocr>path: /tmp/image.png\nlanguage: eng</SKILL>"
    )

    def get_prompt_snippet(self) -> str:
        return self._prompt_snippet

    def run(self, args: str, ctx=None, cfg=None) -> str:
        args = (args or "").strip()
        path_str = ""
        language = "rus+eng"
        for line in args.splitlines():
            line = line.strip()
            if line.startswith("path:"):
                path_str = line[5:].strip()
            elif line.startswith("language:"):
                language = line[9:].strip()
        if not path_str:
            return "[ocr ERROR: path не указан]"
        img_path = Path(path_str).expanduser().resolve()
        if not img_path.exists():
            return f"[ocr ERROR: файл не найден: {path_str}]"
        # Try tesseract first (local, no server needed)
        try:
            import subprocess as _sub
            r = _sub.run(
                ["tesseract", str(img_path), "stdout", "-l", language, "--psm", "6"],
                capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0:
                text = r.stdout.strip()
                return f"[OCR результат]:\n{text}" if text else "[ocr: текст не найден]"
            return f"[ocr ERROR: tesseract вернул {r.returncode}: {r.stderr[:100]}]"
        except FileNotFoundError:
            return (
                "[ocr: tesseract не установлен. Установи: pkg install tesseract\n"
                "или настрой FavoriteChrome для облачного OCR]"
            )
        except Exception as e:
            return f"[ocr ERROR: {e}]"
