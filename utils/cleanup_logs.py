#!/usr/bin/env python3
"""
cleanup_logs.py — утилита для анализа и очистки лог-файлов.
Показывает статистику и может удалить старые/большие логи.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

def get_log_stats(directory="."):
    """Анализ лог-файлов в директории."""
    log_files = []
    
    for f in Path(directory).rglob("*.log"):
        if f.is_file() and "__pycache__" not in str(f):
            try:
                size = f.stat().st_size
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                lines = sum(1 for _ in f.open(encoding="utf-8", errors="ignore"))
                log_files.append({
                    "path": str(f.relative_to(directory)),
                    "size": size,
                    "lines": lines,
                    "mtime": mtime,
                    "age_hours": (datetime.now() - mtime).total_seconds() / 3600
                })
            except Exception:
                pass
    
    return sorted(log_files, key=lambda x: x["size"], reverse=True)


def print_stats(stats):
    """Вывод статистики лог-файлов."""
    if not stats:
        print("Лог-файлы не найдены.")
        return
    
    total_size = sum(f["size"] for f in stats)
    total_lines = sum(f["lines"] for f in stats)
    oldest = min(f["age_hours"] for f in stats)
    newest = max(f["age_hours"] for f in stats)
    
    print("\n📊 Статистика лог-файлов:")
    print(f"  Всего: {len(stats)} файлов")
    print(f"  Общий размер: {total_size / 1024:.1f} KB")
    print(f"  Всего строк: {total_lines:,}")
    print(f"  Старейший: {oldest:.1f} ч. назад")
    print(f"  Новейший: {newest:.1f} ч. назад")
    
    print("\n📁 Список файлов (по убыванию размера):")
    print("-" * 80)
    print(f"{'Файл':<40} {'Размер':>10} {'Строк':>8} {'Возраст':>8}")
    print("-" * 80)
    
    for f in stats:
        size_str = f"{f['size']/1024:>7.2f} KB" if f['size'] < 1024*1024 else f"{f['size']/1024/1024:>6.2f} MB"
        print(f"{f['path']:<40} {size_str:>9} {f['lines']:>8,} {f['age_hours']:>7.1f} ч.")
    
    print("-" * 80)


def suggest_cleanup(stats, min_age_hours=24, max_size_kb=100):
    """Предлагает файлы для удаления."""
    to_delete = []
    
    for f in stats:
        conditions = []
        if f["age_hours"] > min_age_hours:
            conditions.append(f"старее {min_age_hours}ч")
        if f["size"] > max_size_kb * 1024:
            conditions.append(f"> {max_size_kb}KB")
        
        if conditions:
            to_delete.append({**f, "reason": ", ".join(conditions)})
    
    return to_delete


def cleanup_logs(directory=".", dry_run=True):
    """Удаление старых/больших логов (или dry-run)."""
    stats = get_log_stats(directory)
    candidates = suggest_cleanup(stats)
    
    if not candidates:
        print("\n✓ Nothing to clean. Лог-файлы в порядке.")
        return 0
    
    print(f"\n💡 Предлагается удалить {len(candidates)} файлов:")
    for f in candidates:
        action = "[DRY RUN] " if dry_run else ""
        print(f"  {action}✅ {f['path']} ({f['reason']})")
    
    if dry_run:
        print("\n--- Dry run завершён. Запустите без --dry-run для удаления ---")
        return len(candidates)
    
    deleted = 0
    for f in candidates:
        try:
            Path(f["path"]).unlink()
            print(f"  🗑️ Удалено: {f['path']}")
            deleted += 1
        except Exception as e:
            print(f"  ❌ Ошибка удаления {f['path']}: {e}")
    
    print(f"\n✓ Удалено {deleted} файлов")
    return deleted


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Анализ и очистка лог-файлов")
    parser.add_argument("--clean", action="store_true", help="Удалить старые логи")
    parser.add_argument("--dry-run", action="store_true", help="Только показать что будет удалено")
    parser.add_argument("--min-age", type=int, default=24, help="Возраст файла в часах мин для удаления")
    parser.add_argument("--max-size", type=int, default=100, help="Макс размер файла в KB для удаления")
    parser.add_argument("--dir", default=".", help="Директория для анализа")
    
    args = parser.parse_args()
    
    stats = get_log_stats(args.dir)
    print_stats(stats)
    
    if args.clean or not args.dry_run:
        deleted = cleanup_logs(args.dir, dry_run=False)
    else:
        cleanup_logs(args.dir, dry_run=True)
    
    sys.exit(0)
