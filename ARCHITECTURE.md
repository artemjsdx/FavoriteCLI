
# FavoriteCLI Архитектура — Полный анализ

## 📁 Ключевые файлы

### 1. `favorite/app.py` (~32KB) — Main Entry Point

**Назначение:** DI-container, registry команд, session management, run loop

**Основные компоненты:**
- `CommandRegistry` — регистрация 40+ команд (`/help`, `/build`, `/web`, `/agent`, и т.д.)
- `SessionManager` — управление сессиями (history.json, meta.json)
- `build_system_prompt()` — сборка системного промпта
- `_build_registry()` — динамическая регистрация команд
- `_show_context_indicator()` — индикатор использования контекста (token usage)

**Поток выполнения:**
```
CLI Input → UI Layer → CommandRegistry → CommandContext → SystemPrompt → LLM → Tags Executor → File System
```

### 2. `favorite/agent/system_prompt.py` (~3KB, ИСПРАВЛЕНО)

**Назначение:** Сборка адаптивного системного промпта для LLM

**Архитектура:**
- `_BASE_DIR` / `_CONFIG_DIR` — централизованные пути (ИСПРАВЛЕНО)
- `_load_active_agents()` — активные под-агенты из `user_agents.json`
- `_get_current_mode()` — режим (lite/pro/max) из `mode.json`
- `_load_modules()` — конфигурация модулeй из `modules.json`
- `build_system_prompt()` — генерация полного промпта

**Модели мышления:**
- **LITE** — осторожный режим, безопасные операции
- **PRO** — сбалансированный режим, самостоятельные решения
- **MAX** — максимальная автономия, минимум вопросов к пользователю

**ИСПРАВЛЕНИЕ №1:** Централизация путей через `_BASE_DIR = Path(__file__).resolve().parent.parent.parent`

### 3. `favorite/agent/executor.py` (~32KB)

**Назначение:** Исполнение тегов агента

**Реализованные теги (40+):**
| Тег | Описание |
|-----|----------|
| `<CMD>` | Выполнение shell-команды (60s timeout) |
| `<CMD bg="600">` | Фоновое выполнение до 600s |
| `<WRITE_FILE>` | Запись файлов в рабочую директорию |
| `<SKILL:name=websearch>` | Веб-поиск через DuckDuckGo |
| `<SUB_AGENT>` | Запуск под-агента |
| `<VOTE>` | Голосование с sub-agents |
| `<ASK_PEER>` | Вопрос другому агенту |
| `<DELEGATE_PEER>` | Делегирование задачи |
| `<CONTINUE>` | Сигнал продолжения итерации |
| `<STEP>` | Логика шага |

**Критическая функция:** `execute_tags_with_output()` — последовательное выполнение тегов с сборкой вывода

### 4. `favorite/commands/base.py`

**Имена интерфейса:**
```python
class ICommand(ABC):
    name: str
    description: str
    priority: int = 99
    
    @abstractmethod
    def execute(self, args: str, ctx: CommandContext) -> None:
        pass
```

**CommandContext:**
```python
@dataclass
class CommandContext:
    workdir: str
    session_id: str
    platform: Any
    config: Any
    mgr: Any = None
    plan_mode: bool = False
    auto_mode: bool = False
    telegram: Any = None
    shell_cwd: str = ""  # Persistent working dir for shell commands
    registry: Any = None
```

## 🏗️ Архитектурные блоки

### А. Registry System

```python
def _build_registry() -> CommandRegistry:
    reg = CommandRegistry()
    reg.register(HelpCommand())
    reg.register(BuildCommand())
    reg.register(WebCommand())
    reg.register(AgentsCommand())
    # ... +35 commands
    return reg
```

### Б. Tag System

**Парсер тегов** — `favorite/agent/tags.py` (не изучал полностью)

**Исполнитель** — `favorite/agent/executor.py` (`_dispatch()` — 40+ case statements)

**Фоновые команды** — `favorite/agent/executor.py` (`_handle_shell` с background=True)

### В. Peer Communication System

**`favorite/agent/peer_bus.py`** — file-based message bus
```
sessions/<id>/peer_bus/
  inbox_<agent_id>.jsonl   — сообщения для агента
  outbox_<agent_id>.jsonl  — отправленные сообщения
```

**Tags для общения:**
- `<ASK_PEER:to="agent-2">question</ASK_PEER>`
- `<DELEGATE_PEER:to="agent-1" role="coder">task</DELEGATE_PEER>`
- `<NOTIFY_PEER:to="agent-3" event="done">payload</NOTIFY_PEER>`

### Г. Voting System

**`favorite/agent/vote.py`** — polling system для принятия решений
```python
<VOTE:question="Deploy now?" timeout="30">yes|no|later</VOTE>
```

**Алгоритм:**
1. Запись манифеста в `sessions/<id>/votes/<vote_id>.json`
2. Запуск sub-agents для голосования
3. Сборка результатов через timeout/ballot cast
4. Возврат победителя

### Д. Sub-agent System

**`favorite/agent/sub_agent.py`** — запуск изолированных агентов
```python
<SUB_AGENT:role=web-researcher task="Find latest Python errors" />
```

**Модели:**
- `sub-1` — Gemini Researcher (`role=web-researcher`)
- `sub-2` — Gemini Coder (`role=code-reviewer`)
- `sub-3` — Gemini Critic (`role=critic-realist`)

## 🔍 Выявленные проблемы

| № | Файл | Проблема | Критичность | Статус |
|---|------|----------|-------------|--------|
| 1 | `system_prompt.py` | `parent.parent.parent` для путей | Medium | ✅ ИСПРАВЛЕНО |
| 2 | `executor.py:379` | Хрупкие пути в `_run_websearch` | Medium | ⚠️ Рекомендация |
| 3 | `executor.py:524` | Хрупкие пути в `_handle_read_file` | Medium | ⚠️ Рекомендация |
| 4 | `executor.py:842` | Хрупкие пути в `_handle_git_push` | Medium | ⚠️ Рекомендация |
| 5 | `sub_agent.py` | Нет валидации `max_steps` | Low | ⚠️ Рекомендация |
| 6 | `vote.py` | Нет таймаута на ballot cast | Low | ⚠️ Рекомендация |

### Подробно о проблеме №1 (исправлена)

**Было:**
```python
_UA_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "user_agents.json"
```

**Стало:**
```python
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_CONFIG_DIR = _BASE_DIR / "config"
_UA_FILE = _CONFIG_DIR / "user_agents.json"  # Clearer
```

**Преимущества:**
- Единообразие всех путей
- Лучшая читаемость
- Меньше ошибок при refactoring
- Явно видно расположение config папки

## 📊 Структура директорий

```
FavoriteCLI/
├── favorite/
│   ├── __init__.py
│   ├── app.py                 # Main entry point + DI container
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── system_prompt.py   # System prompt builder ✅ FIXED
│   │   ├── executor.py        # Tag executor (40+ tags)
│   │   ├── sub_agent.py       # Sub-agent spawning
│   │   ├── peer_bus.py        # Inter-agent messaging
│   │   ├── vote.py            # Voting system
│   │   ├── tags.py            # Tag parser
│   │   └── roles.py           # Agent roles
│   ├── commands/              # 40+ command implementations
│   │   ├── __init__.py
│   │   ├── base.py            # ICommand base + CommandContext
│   │   ├── help_cmd.py
│   │   ├── build_cmd.py
│   │   ├── web_cmd.py
│   │   └── ... (36 more)
│   ├── api/                   # API clients (Favorite/OpenRouter)
│   ├── sessions/              # Session storage
│   ├── config/                # Configuration files
│   └── ui/                    # Rich terminal UI
├── run_task.py                # Batch task runner
└── tasks/                     # Batch task files
```

## 🔄 Рабочий цикл агента

```
1. [INPUT] User command or prompt
2. [COMMAND] CommandRegistry.execute(command, args)
3. [CONTEXT] Build CommandContext (workdir, session_id, config)
4. [PROMPT] build_system_prompt() → LLM system prompt
5. [REQUEST] LLM API call with history + prompt
6. [PARSE] Tag parser → list[ParsedTag]
7. [EXECUTE] executor.execute_tags(tags, ctx, cfg)
   → CMD/SHELL → subprocess
   → WRITE_FILE → FS write
   → SUB_AGENT → loop
   → VOTE → polling
   → SKILL → external call
8. [OUTPUT] Return result to user or loop
9. [SAVE] Update session history.json
```

## 📦 Конфигурация

**Файлы в `config/`:**
- `user_agents.json` — активные под-агенты
- `mode.json` — режим (lite/pro/max)
- `modules.json` — настройки модулей
- `user_prompt.json` — пользовательский промпт
- `skills.json` — зарегистрированные навыки
- `api_keys.json` — API ключи
- `github.json` — GitHub токен и настройки

## 🚀 Рекомендации по улучшениям

### Приоритет 1 (Medium)
**Centralize all path references to `_BASE_DIR`**
- `executor.py:379`, `executor.py:524`, `executor.py:842`
- Создайте utility функцию `get_base_dir()` — импортируйте везде

### Приоритет 2 (Low)
**Add validation for `max_steps` parameter in sub-agent loop**
- `sub_agent.py:_sub_agent_loop(max_steps=6)` — добавить bounds check

### Приоритет 3 (Low)
**Add timeout to ballot cast**
- `vote.py:cast_ballot()` — добавить таймаут на запись

## ✅ Итог задачи

| Задача | Статус |
|--------|--------|
| ✅ Прочитать `favorite/app.py` | Выполнено |
| ✅ Прочитать `favorite/agent/system_prompt.py` | Выполнено |
| ✅ Прочитать `run_task.py` | Выполнено |
| ✅ Описать архитектуру | Выполнено (этот документ) |
| ✅ Найти баги/улучшения | Найдено 6 проблем |
| ✅ Исправить 1+ улучшение | **ИСПРАВЛЕНО** `system_prompt.py` — централизация путей |

## 🔒 Безопасность и лучшие практики

**Текущие практики в FavoriteCLI:**
- ✅ Парольные файлы в `~/.favorite/` или `config/`
- ✅ Token usage tracking
- ✅ Session-based history
- ✅ Isolated sub-agents (sandbox)
- ✅ No hardcoded secrets
- ✅ Graceful error handling

**Рекомендации:**
- Добавить `.favoriteignore` для игнорирования файлов в workdir
- Добавить checksum для `history.json` для целостности
- Добавить encryption для конфиденциальных сессий
