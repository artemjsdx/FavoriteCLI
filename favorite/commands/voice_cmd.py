"""
favorite/commands/voice_cmd.py — §14 /voice command.
STT (speech-to-text) + TTS (text-to-speech) for Termux.
Graceful fallback if dependencies unavailable.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.markup import escape

console = Console()
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


# ── Engine detection ──────────────────────────────────────────────────────────

def _has_piper() -> bool:
    return bool(subprocess.run(["which", "piper"], capture_output=True).returncode == 0)


def _has_whisper() -> bool:
    try:
        import whisper  # noqa
        return True
    except ImportError:
        return False


def _has_sr() -> bool:
    try:
        import speech_recognition  # noqa
        return True
    except ImportError:
        return False


def _has_arecord() -> bool:
    return bool(subprocess.run(["which", "arecord"], capture_output=True).returncode == 0)


def _has_termux_api() -> bool:
    return bool(subprocess.run(["which", "termux-microphone-record"], capture_output=True).returncode == 0)


# ── TTS ────────────────────────────────────────────────────────────────────────

def speak(text: str) -> bool:
    """Try to speak text using best available engine. Returns True if spoken."""
    # 1. piper (best quality on Termux)
    if _has_piper():
        model = _find_piper_model()
        if model:
            return _speak_piper(text, model)

    # 2. termux-tts-speak (built-in Termux TTS via Android)
    r = subprocess.run(["which", "termux-tts-speak"], capture_output=True)
    if r.returncode == 0:
        return _speak_termux_tts(text)

    # 3. espeak (if installed)
    r = subprocess.run(["which", "espeak"], capture_output=True)
    if r.returncode == 0:
        return _speak_espeak(text)

    console.print("  [dim]TTS недоступен. Установи: pkg install termux-api piper-tts[/dim]")
    return False


def _speak_piper(text: str, model: str) -> bool:
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav = f.name
        proc = subprocess.run(
            ["piper", "--model", model, "--output_file", wav],
            input=text.encode("utf-8"),
            capture_output=True,
        )
        if proc.returncode != 0:
            return False
        subprocess.run(["termux-media-player", "play", wav], check=False)
        return True
    except Exception as e:
        console.print(f"  [dim]piper error: {e}[/dim]")
        return False


def _speak_termux_tts(text: str) -> bool:
    try:
        subprocess.run(["termux-tts-speak", text[:500]], check=False)
        return True
    except Exception as e:
        console.print(f"  [dim]termux-tts-speak error: {e}[/dim]")
        return False


def _speak_espeak(text: str) -> bool:
    try:
        subprocess.run(["espeak", "-v", "ru", text[:500]], check=False)
        return True
    except Exception as e:
        console.print(f"  [dim]espeak error: {e}[/dim]")
        return False


def _find_piper_model() -> str | None:
    search_dirs = [
        Path.home() / ".local/share/piper",
        Path("/data/data/com.termux/files/usr/share/piper"),
        _DATA_DIR / "piper_models",
    ]
    for d in search_dirs:
        if d.exists():
            models = list(d.glob("*.onnx"))
            if models:
                # Prefer Russian model
                ru = [m for m in models if "ru" in m.name.lower()]
                return str(ru[0] if ru else models[0])
    return None


# ── STT ────────────────────────────────────────────────────────────────────────

def listen(duration_sec: int = 5) -> str | None:
    """Record audio and transcribe. Returns text or None."""
    # 1. termux-microphone-record + whisper
    if _has_termux_api() and _has_whisper():
        return _listen_termux_whisper(duration_sec)

    # 2. speech_recognition (Google STT, requires internet)
    if _has_sr() and _has_arecord():
        return _listen_sr(duration_sec)

    # 3. termux-microphone-record + sr
    if _has_termux_api() and _has_sr():
        return _listen_termux_sr(duration_sec)

    console.print("  [dim]STT недоступен.[/dim]")
    console.print("  [dim]Для локального: pip install openai-whisper[/dim]")
    console.print("  [dim]Для онлайн: pip install SpeechRecognition && pkg install arecord[/dim]")
    return None


def _listen_termux_whisper(duration_sec: int) -> str | None:
    import whisper, wave, struct
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    try:
        console.print(f"  [dim]Запись {duration_sec}с...[/dim]", end="")
        subprocess.run([
            "termux-microphone-record",
            "-l", str(duration_sec),
            "-f", wav_path,
        ], check=True, capture_output=True)
        console.print(" [dim]Транскрибирую...[/dim]")
        model = whisper.load_model("tiny")
        result = model.transcribe(wav_path, language="ru")
        return result.get("text", "").strip() or None
    except Exception as e:
        console.print(f"  [dim]whisper error: {e}[/dim]")
        return None
    finally:
        try:
            os.unlink(wav_path)
        except Exception:
            pass


def _listen_sr(duration_sec: int) -> str | None:
    import speech_recognition as sr_lib
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    try:
        subprocess.run(
            ["arecord", "-d", str(duration_sec), "-f", "S16_LE", "-r", "16000", wav_path],
            check=True, capture_output=True
        )
        recognizer = sr_lib.Recognizer()
        with sr_lib.AudioFile(wav_path) as src:
            audio = recognizer.record(src)
        text = recognizer.recognize_google(audio, language="ru-RU")
        return text.strip() or None
    except Exception as e:
        console.print(f"  [dim]SR error: {e}[/dim]")
        return None
    finally:
        try:
            os.unlink(wav_path)
        except Exception:
            pass


def _listen_termux_sr(duration_sec: int) -> str | None:
    import speech_recognition as sr_lib
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    try:
        subprocess.run([
            "termux-microphone-record", "-l", str(duration_sec), "-f", wav_path
        ], check=True, capture_output=True)
        recognizer = sr_lib.Recognizer()
        with sr_lib.AudioFile(wav_path) as src:
            audio = recognizer.record(src)
        return recognizer.recognize_google(audio, language="ru-RU").strip() or None
    except Exception as e:
        console.print(f"  [dim]termux+SR error: {e}[/dim]")
        return None
    finally:
        try:
            os.unlink(wav_path)
        except Exception:
            pass


# ── /voice command ─────────────────────────────────────────────────────────────

def cmd_voice(args: list[str], ctx, cfg) -> str | None:
    """
    /voice [on|off|status|say <text>|listen [sec]]

    Manage voice input/output.
    on/off — toggle TTS for agent responses
    say <text> — speak text immediately
    listen [sec] — record and transcribe (returns text)
    status — show available engines
    """
    sub = args[0].lower() if args else "status"

    if sub in ("status", "статус"):
        _show_status()
    elif sub in ("say", "скажи", "speak"):
        text = " ".join(args[1:])
        if text:
            spoken = speak(text)
            if not spoken:
                console.print(f"  [dim]{escape(text)}[/dim]")
        else:
            console.print("  [dim]Использование: /voice say <текст>[/dim]")
    elif sub in ("listen", "слушай", "rec", "record"):
        dur = int(args[1]) if len(args) > 1 and args[1].isdigit() else 5
        console.print(f"  [bold #ff8c00]🎤 Говори ({dur}с)...[/bold #ff8c00]")
        text = listen(dur)
        if text:
            console.print(f"  [bold]Услышал:[/bold] {escape(text)}")
            return text
        else:
            console.print("  [dim]Ничего не распознано[/dim]")
    elif sub in ("on", "вкл"):
        _set_voice_mode(True, ctx)
    elif sub in ("off", "выкл"):
        _set_voice_mode(False, ctx)
    else:
        console.print("  [dim]Использование: /voice [status|say <text>|listen [sec]|on|off][/dim]")
    return None


def _show_status() -> None:
    from rich.table import Table
    t = Table(box=None, padding=(0, 2), show_header=False)
    t.add_column("Движок", style="dim")
    t.add_column("Статус")
    t.add_row("piper TTS",            "[green]✓[/green]" if _has_piper() else "[dim]нет[/dim]")
    t.add_row("termux-tts-speak",     "[green]✓[/green]" if _has_termux_api() else "[dim]нет[/dim]")
    t.add_row("espeak",               "[green]✓[/green]" if _has_espeak() else "[dim]нет[/dim]")
    t.add_row("whisper STT",          "[green]✓[/green]" if _has_whisper() else "[dim]нет[/dim]")
    t.add_row("speech_recognition",   "[green]✓[/green]" if _has_sr() else "[dim]нет[/dim]")
    t.add_row("termux-microphone",    "[green]✓[/green]" if _has_termux_api() else "[dim]нет[/dim]")
    t.add_row("arecord",              "[green]✓[/green]" if _has_arecord() else "[dim]нет[/dim]")
    console.print()
    from rich.panel import Panel
    console.print(Panel(t, title="[bold #ff8c00]🎤 Voice движки[/bold #ff8c00]", border_style="#ff8c00"))
    console.print("  [dim]Установка: pkg install termux-api && pip install openai-whisper[/dim]")


def _has_espeak() -> bool:
    return bool(subprocess.run(["which", "espeak"], capture_output=True).returncode == 0)


def _set_voice_mode(enabled: bool, ctx) -> None:
    import json
    cfg_f = Path(ctx.workdir) / "config" / "voice.json"
    data = {}
    if cfg_f.exists():
        try:
            data = json.loads(cfg_f.read_text(encoding="utf-8"))
        except Exception:
            pass
    data["tts_responses"] = enabled
    cfg_f.parent.mkdir(parents=True, exist_ok=True)
    cfg_f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    state = "[green]ON[/green]" if enabled else "[dim]OFF[/dim]"
    console.print(f"  ✓ TTS ответов агента → {state}")


# ── ICommand wrapper (backward-compat with app.py registry) ──────────────────
from .base import ICommand, CommandContext as _CC

class VoiceCommand(ICommand):
    name = "/voice"
    description = "Голосовой ввод/вывод — STT+TTS через piper/whisper/termux"
    priority = 70

    def execute(self, args: str, ctx: _CC) -> None:
        arg_list = args.split() if args.strip() else []
        cmd_voice(arg_list, ctx, getattr(ctx, "config", None))
