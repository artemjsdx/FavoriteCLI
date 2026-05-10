#!/usr/bin/env python3
"""
FavoriteCLI — CLI AI-agent for Termux/Android.
Entry point. Run: python favorite.py
"""
import os
import sys

# Фикс дублирования ввода в Termux/Android
os.environ.setdefault("TERM", "xterm-256color")


def main():
    try:
        from favorite.app import run
        run()
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
