#!/usr/bin/env python3
"""
gen_readme.py — генератор README.md для проектов на Python.
Извлекает мета-информацию из setup.py/pyproject.toml и создаёт документацию.
"""
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

def read_file(path):
    """Читает файл, если существует."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""


def extract_project_info(directory="."):
    """Извлекает информацию о проекте из файлов."""
    info = {
        "name": "my-project",
        "description": "",
        "version": "0.1.0",
        "author": "",
        "year": datetime.now().year,
        "python_requires": ">=3.8",
        "dependencies": [],
        "cli_commands": []
    }
    
    # Читаем setup.py
    setup_content = read_file("setup.py")
    if setup_content:
        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', setup_content)
        if match:
            info["name"] = match.group(1)
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', setup_content)
        if match:
            info["version"] = match.group(1)
        match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', setup_content)
        if match:
            info["description"] = match.group(1)
        match = re.search(r'author\s*=\s*["\']([^"\']+)["\']', setup_content)
        if match:
            info["author"] = match.group(1)
        match = re.search(r'install_requires\s*=\s*\[([^\]]+)\]', setup_content)
        if match:
            reqs = re.findall(r'["\']([^"\']+)["\']', match.group(1))
            info["dependencies"] = [r.strip() for r in reqs if r]
    
    # Читаем pyproject.toml
    toml_content = read_file("pyproject.toml")
    if toml_content:
        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', toml_content)
        if match:
            info["name"] = match.group(1)
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', toml_content)
        if match:
            info["version"] = match.group(1)
        match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', toml_content)
        if match:
            info["description"] = match.group(1)
    
    # Читаем requirements.txt
    reqs_content = read_file("requirements.txt")
    if reqs_content:
        for line in reqs_content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                dep = line.split("[")[0].split("=")[0].split(">")[0].split("<")[0].split("~")[0].strip()
                if dep and dep not in info["dependencies"]:
                    info["dependencies"].append(dep)
    
    # Собираем CLI команды из favorite/commands если существует
    commands_dir = Path(directory) / "favorite" / "commands"
    if commands_dir.exists():
        for cmd_file in commands_dir.glob("*.py"):
            if cmd_file.name.startswith("_") or cmd_file.name == "base.py":
                continue
            content = cmd_file.read_text(encoding="utf-8")
            match = re.search(r'class\s+(\w+Command)\s*\(', content)
            if match:
                cmd_name = match.group(1).replace("Command", "").lower()
                if cmd_name not in info["cli_commands"] and len(info["cli_commands"]) < 10:
                    info["cli_commands"].append(cmd_name)
    
    return info


def generate_readme(info):
    """Генерирует содержимое README.md."""
    
    deps_section = ""
    if info["dependencies"]:
        deps = "\n".join(f"- `{dep}`" for dep in info["dependencies"][:10])
        deps_section = f"""
## 📦 Зависимости

Проект требует следующие Python-пакеты:

{deps}
"""
    else:
        deps_section = """
## 📦 Зависимости

Проект имеет минимальный набор зависимостей. Установите требования:

```bash
pip install -r requirements.txt
```
"""
    
    commands_section = ""
    if info["cli_commands"]:
        commands_list = "\n".join(f"- `{cmd}`" for cmd in info["cli_commands"])
        commands_section = f"""
## 💻 Команды CLI

Проект предоставляет следующие команды:

{commands_list}

Для полного списка команд используйте:

```bash
{info["name"].replace('-', ' ')} --help
```
"""
    else:
        commands_section = """
## 💻 Команды CLI

Используйте `--help` для просмотра доступных команд и опций.
"""
    
    readme_template = f"""# {info["name"]}

> Версия: `{info["version"]}` │ © {info["year"]}

{info["description"] or "Описание проекта будет здесь..." }

---

## 🚀 Быстрый старт

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/{info["name"]}.git
cd {info["name"]}

# Установка зависимостей
pip install -r requirements.txt

# Запуск (если есть CLI)
{info["name"].replace('-', ' ')} --help
```

## 📦 Установка

### pip

```bash
pip install -e .
```

### Из репозитория

```bash
git clone https://github.com/yourusername/{info["name"]}.git
cd {info["name"]}
pip install -r requirements.txt
```

## 💻 Команды CLI

Проект поддерживает следующие команды:

- `{info["name"].replace('-', ' ')} --help` — общая справка
- `{info["name"].replace('-', ' ')} doctor` — диагностика проекта
- `{info["name"].replace('-', ' ')} agents` — управление агентами

> Используйте `--help` после любой команды для просмотра деталей.

## 📁 Структура проекта

```
{info["name"]}/
├── favorite/       # Основная кодовая база
├── config/         # Файлы конфигурации
├── docs/           # Документация
├── utils/          # Вспомогательные утилиты
├── requirements.txt
├── setup.py
└── README.md
```

## 🛠️ Разработка

```bash
# Установка для разработки
pip install -r requirements.txt -r requirements-dev.txt

# Запуск
python -m favorite.app

# Тесты
pytest
```

## 📄 License

© {info["year"]} {info["author"] or "Author"}. All rights reserved.

## 🤝 Contributing

Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

*Сгенерировано генератором README*
"""
    
    return readme_template


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Генератор README.md для проектов")
    parser.add_argument("--output", "-o", default="README.md", help="Выходной файл")
    parser.add_argument("--force", "-f", action="store_true", help="Переписать существующий файл")
    parser.add_argument("--dir", "-d", default=".", help="Директория для анализа")
    parser.add_argument("--preview", "-p", action="store_true", help="Только показать превью")
    
    args = parser.parse_args()
    
    output_path = Path(args.output)
    
    if output_path.exists() and not args.force:
        print(f"❌ Файл '{args.output}' уже существует. Используйте --force для перезаписи.")
        return 1
    
    print("📊 Анализ проекта...")
    info = extract_project_info(args.dir)
    
    print(f"✏️  Название: {info['name']}")
    print(f"📌 Версия: {info['version']}")
    print(f"📦 Пакетов: {len(info['dependencies'])}")
    print(f"🎯 Команд CLI: {len(info['cli_commands'])}")
    
    readme = generate_readme(info)
    
    if args.preview:
        print("\n--- ПРЕВЬЮ README.md ---\n")
        print(readme)
        return 0
    
    try:
        output_path.write_text(readme, encoding="utf-8")
        print(f"\n✅ README.md успешно создан в '{args.output}'!")
        return 0
    except Exception as e:
        print(f"\n❌ Ошибка записи: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
