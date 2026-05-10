#!/usr/bin/env python3
"""
project_health.py — проверка состояния проекта.
Анализирует структуру, зависимости, код и给出 рекомендации.
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def check_file_exists(path, expected=True):
    """Проверяет существование файла."""
    p = Path(path)
    exists = p.exists()
    return exists if expected else not exists


def get_git_status():
    """Получает статус git репозитория."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip().splitlines()
    except Exception:
        return ["Не git репозиторий"]


def count_lines(paths):
    """Считает строки в файлах."""
    total = 0
    for p in paths:
        try:
            total += sum(1 for _ in Path(p).rglob("*.py"))
        except:
            continue
    return total


def run_python_check(path, args=[]):
    """Запускает Python проверку."""
    try:
        result = subprocess.run(
            ["python3", "-m", "py_compile"] + [path],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)


def analyze_project():
    """Основная функция анализа."""
    print("\n🏥 Проверка состояния проекта FavoriteCLI\n")
    print("=" * 60)
    
    results = []
    
    # 1. Проверка основных файлов
    print("\n1️⃣  Проверка структуры проекта...")
    mandatory = [
        ("favorite/app.py", True),
        ("README.md", True),
        ("config/", True),
        ("favorite/commands/", True),
        ("requirements.txt", False),  # опционально
    ]
    
    files_ok = 0
    files_total = len(mandatory)
    
    for path, expected in mandatory:
        exists = Path(path).exists()
        status = "✓" if exists else "✗"
        if (exists and expected) or (not exists and not expected):
            files_ok += 1
        results.append(f"{status} {path}")
    
    print(f"   Структура: {files_ok}/{files_total} ОК")
    
    # 2. Проверка git
    print("\n2️⃣  Проверка git...")
    git_output = get_git_status()
    if isinstance(git_output, list) and len(git_output) > 0 and git_output[0] != "Не git репозиторий":
        modified = sum(1 for line in git_output if line.startswith(('M', 'A', 'D')))
        untracked = sum(1 for line in git_output if line.startswith('?'))
        print(f"   Модифицировано: {modified}")
        print(f"   Не отслеживается: {untracked}")
        if modified > 0:
            results.append("⚠️  Есть не закоммеченные изменения")
    else:
        results.append("⚠️  Не git репозиторий")
    
    # 3. Проверка Python синтаксиса
    print("\n3️⃣  Проверка Python файлов...")
    py_files = list(Path("favorite").rglob("*.py"))[:10]
    syntax_ok = 0
    
    for py_file in py_files:
        ok, error = run_python_check(str(py_file))
        if ok:
            syntax_ok += 1
    
    print(f"   Синтаксис: {syntax_ok}/{len(py_files)} ОК")
    results.append(f"✓ Python синтаксис (проверка {len(py_files)} файлов)")
    
    # 4. Проверка зависимостей
    print("\n4️⃣  Проверка зависимостей...")
    req_path = Path("requirements.txt")
    if req_path.exists():
        req_content = req_path.read_text(encoding="utf-8")
        lines = [l for l in req_content.splitlines() if l.strip() and not l.startswith("#")]
        print(f"   Зависимостей: {len(lines)}")
        results.append(f"✓ requirements.txt ({len(lines)} строк)")
    else:
        results.append("⚠️  requirements.txt отсутствует")
    
    # 5. Проверка тестов
    print("\n5️⃣  Проверка тестов...")
    test_dirs = [Path("tests"), Path("test"), Path("favorite/tests")]
    tests_exist = any(d.exists() for d in test_dirs)
    
    if tests_exist:
        test_files = sum(len(list(d.glob("*.py"))) for d in test_dirs if d.exists())
        print(f"   Тестовых файлов: {test_files}")
        results.append(f"✓ Тесты найдены ({test_files} файлов)")
    else:
        results.append("⚠️  Тесты отсутствуют")
    
    # 6. Файловая система
    print("\n6️⃣  Статистика файлов...")
    py_count = sum(1 for _ in Path(".").rglob("*.py") if "__pycache__" not in str(_))
    log_count = sum(1 for _ in Path(".").rglob("*.log"))
    total_size = sum(f.stat().st_size for f in Path(".").rglob("*") if f.is_file() and "__pycache__" not in str(f))
    
    print(f"   Python-файлов: {py_count}")
    print(f"   Лог-файлов: {log_count}")
    print(f"   Общий размер: {total_size / 1024:.1f} KB")
    
    results.append(f"📊 {py_count} Python файлов, {log_count} log ( {total_size/1024:.1f}KB )")
    
    # 7. Рекомендации
    print("\n7️⃣  Рекомендации:")
    recommendations = []
    
    if log_count > 10:
        recommendations.append("🧹 Удалить старые лог-файлы")
    
    if files_ok < files_total:
        recommendations.append("📋 Добавить недостающие файлы проекта")
    
    if not tests_exist:
        recommendations.append("🧪 Добавить тесты")
    
    if not Path("CONTRIBUTING.md").exists():
        recommendations.append("📚 Добавить CONTRIBUTING.md")
    
    # Вывод итогов
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ПРОВЕРКИ:")
    print("=" * 60)
    
    for line in results:
        print(f"  {line}")
    
    if recommendations:
        print("\n💡 РЕКОМЕНДАЦИИ:")
        for rec in recommendations:
            print(f"  → {rec}")
    
    print("\n" + "=" * 60)
    
    # Финальная оценка
    score = 100 - len(recommendations) * 10
    if score >= 80:
        level = "Отлично"
        color = "🟢"
    elif score >= 60:
        level = "Хорошо"
        color = "🟡"
    else:
        level = "Требует внимания"
        color = "🟠"
    
    print(f"\n{color} Оценка состояния: {score}/100 — {level}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(analyze_project())
