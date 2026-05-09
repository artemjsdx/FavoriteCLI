# FavoriteCLI Skills System

  Скиллы — это расширения агента FavoriteCLI. Каждый скилл: Python-класс + .md-описание.

  ## Как добавить скилл

  1. Создай `favorite/skills/my_skill.py` с классом, наследующим `ISkill`:

  ```python
  from .base import ISkill

  class MySkill(ISkill):
      name = "my_skill"
      description = "Что делает этот скилл"
      
      def run(self, args: str, ctx=None, cfg=None) -> str:
          return f"результат: {args}"
  ```

  2. Добавь описание для агента в `favorite/skills/my_skill.md`

  3. Зарегистрируй в `favorite/skills/__init__.py`:
  ```python
  ("my_skill", "favorite.skills.my_skill", "MySkill"),
  ```

  4. Добавь в `config/skills.json`:
  ```json
  "my_skill": {"enabled": false, "lazy": true, "description": "..."}
  ```

  5. Агент вызывает скилл через тег: `<SKILL:name=my_skill>аргументы</SKILL>`
  6. Пользователь включает: `/skills my_skill on`

  ## Встроенные скиллы

  | Скилл | Описание | По умолчанию |
  |-------|----------|--------------|
  | websearch | Поиск в DuckDuckGo | ✓ |
  | fetch_url | Загрузка веб-страниц | ✓ |
  | fs_tools | Работа с файлами (read/write/list) | ✓ |
  | compaction | Сжатие истории диалога | ✓ |
  | retry | Управление повторными попытками | ✓ |
  | hooks | Lifecycle-хуки (on_done, on_push...) | off |
  | auto_context | Автоматический поиск релевантных файлов | off |
  | web_panel | Веб-дашборд FastAPI | off |
  | internet | Браузерная автоматизация (FavoriteChrome) | off |
  | ocr | OCR — распознавание текста с картинок | off |
  | markitdown | Конвертация документов в Markdown | off |
  