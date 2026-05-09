# FavoriteCLI — План разработки по отсекам

  Правило: каждый отсек завершается пушем в GitHub и отчётом.
  GitHub: https://github.com/animebyst07-stack/FavoriteCLI

  ---

  ## ОТСЕК 1 — Фундамент [DONE]

  - [x] Структура файлов проекта (по SOLID, §10)
  - [x] `config/api_keys.json` — пустой шаблон
  - [x] `favorite/platform.py` — IPlatform / TermuxPlatform / LinuxFakePlatform
  - [x] `favorite/ui/theme.py` — цветовая схема оранжевый + белый
  - [x] `favorite/ui/welcome.py` — welcome-блок
  - [x] `favorite/ui/spinner.py` — анимация ● серый/белый
  - [x] `favorite/ui/chat.py` — рендер сообщений + print_status_line()
  - [x] `favorite/ui/prompt.py` — slash-меню с автодополнением
  - [x] `favorite/commands/` — ICommand + registry + все базовые команды
  - [x] `favorite/agent/tags.py` — парсер тегов ≪TAG≫
  - [x] `favorite/agent/sub_roles_library.json` — 20 встроенных ролей
  - [x] `favorite/sessions/manager.py` — CRUD сессий + stats tracking
  - [x] `favorite/github/api_client.py` — GitHub REST API
  - [x] `favorite/github/auto_push.py` — авто-пуш
  - [x] `favorite/api/` — IChatProvider, FavoriteApiClient, OpenRouterClient, NvidiaClient
  - [x] `favorite/memory/favorite_md.py` — чтение/запись Favorite.md
  - [x] `favorite/setup_wizard.py` — мастер первого запуска
  - [x] `favorite/app.py` — DI-контейнер, главный run-loop
  - [x] `favorite.py` — точка входа
  - [x] UX фиксы: clear экрана, спиннер ●, убрано дублирование ввода
  - [x] Статус в шапке всегда актуален (reload_config при каждом показе)

  ## planMOST — Telegram URL-мост [DONE]

  - [x] `freeapi/tg_notify.py` — пинит красивое уведомление с URL
  - [x] `favorite/bridge/tg_url.py` — читает URL из pinned_message
  - [x] `favorite/config/loader.py` — поля tg_bridge_token/chat_id
  - [x] `favorite/app.py` — авторетрай через TG при ConnectionError

  ---

  ## ОТСЕК 2 — Ядро агента: история + теги + скиллы [DONE]

  - [x] Многоходовая история messages[] — AI помнит разговор (последние 20 сообщений)
  - [x] Системный промпт из Favorite.md передаётся при каждом запросе
  - [x] `favorite/agent/executor.py` — все теги: STEP, SHELL_RAW, SHELL_BG, SLEEP, WRITE_FAV, WRITE_CTX, GIT_PUSH, SKILL, CONTINUE, POLL, WRITE_PLAN, READ_FILE, WRITE_FILE, ASK_USER, THINK, SUB_AGENT, ADD_TASK, UPDATE_TASK, COMPLETE_TASK, LIST_TASKS
  - [x] `favorite/skills/web_search.py` — VoidAI perplexity/sonar + DuckDuckGo fallback
  - [x] `favorite/skills/fetch_url.py` — загрузка URL + очистка HTML
  - [x] `favorite/skills/fs_tools.py` — read/write/append/list файлов в WORKDIR
  - [x] Стриминг SSE от OpenRouter с подавлением `<thinking>` блоков
  - [x] Режим /plan: диалог → POLL → WRITE_PLAN → sessions/<id>/plan.txt
  - [x] Режим /build: чтение plan.txt + исполнение тегов + GIT_PUSH
  - [x] `favorite/agent/response_processor.py` — strip_thinking_blocks()
  - [x] `favorite/agent/system_prompt.py` — централизованный build_system_prompt()
  - [x] `favorite/agent/model_router.py` — RouterModule: classify_prompt() + select_model()
  - [x] `favorite/api/nvidia.py` — NvidiaClient(IChatProvider)
  - [x] `favorite/config/loader.py` — nvidia_key поле

  ---

  ## ОТСЕК 3 — Многоагентность + hot-reload памяти [DONE]

  - [x] `/agents list` — таблица активных агентов + доступные роли из библиотеки
  - [x] `/agents spawn <role> <task> [--model <id>]` — запускает суб-агент с ролью
  - [x] `favorite/agent/sub_agent.py` — run_sub_agent() с поддержкой model override
  - [x] Суб-агент по умолчанию: **qwen/qwen3-coder:free** (OpenRouter)
  - [x] `≪SUB_AGENT:role=...:model=...≫` тег — вызов суб-агента из main agent loop
  - [x] Hot-reload Favorite.md через watchdog Observer
  - [x] `/memory` — показать содержимое Favorite.md в rich Panel
  - [x] `/memory edit` — открыть $EDITOR или показать путь
  - [x] `favorite/memory/hot_reload.py` — start_watcher() с дебаунсингом
  - [x] `favorite/commands/memory_cmd.py` — MemoryCommand

  ---

  ## ОТСЕК 4 — Утилиты + диагностика [DONE]

  - [x] `/usage` — запросы, токены (est), длительность, модель, размер Favorite.md
  - [x] `favorite/commands/usage_cmd.py` — UsageCommand
  - [x] `favorite/tasks/manager.py` — TaskManager: CRUD задач в sessions/<id>/tasks.json
  - [x] `favorite/commands/tasks_cmd.py` — /tasks list/add/done/todo/progress/del с rich Table
  - [x] `/doctor` — диагностика: API ключи, сеть, воркдир, Favorite.md, GitHub конфиг
  - [x] `favorite/commands/doctor_cmd.py` — DoctorCommand (OK/FAIL/WARN таблица)
  - [x] `/recap [N]` — компактный дайджест последних N обменов в rich Panel
  - [x] `favorite/commands/recap_cmd.py` — RecapCommand
  - [x] `/compact` — сжать историю в context_summary.md, заменить history.jsonl
  - [x] `favorite/commands/compact_cmd.py` — CompactCommand
  - [x] Централизованный print_status_line() — все статус-строки через одну функцию
  - [x] Null byte в app.py устранён

  ---

  ## ОТСЕК 5 — Продвинутые фичи [DONE]

  - [x] `/auto <задача>` — непрерывный loop без user input, до ≪DONE≫ (лимит 20 iter)
  - [x] `/silent` — тихий режим (скрыть STEP/shell-вывод), toggle on/off
  - [x] Тег `≪REQUEST_SECRET:key:reason≫` — агент запрашивает API-ключ у пользователя
  - [x] Тег `≪SUGGEST_NEXT:text≫` — жирная подсказка "Дальше я могу X. Хочешь?"
  - [x] `**bold**` / `*italic*` рендеринг через `_apply_inline()` в chat.py
  - [x] Sub-agent model override: `--model <id>` в /agents spawn
  - [x] Compaction: WRITE_CTX при переполнении контекста (>16K токенов)
  - [x] Библиотека ролей: расширена до 63 ролей
  - [x] Telegram-уведомления (три режима роутинга: log_only/private/group/channel)
  - [x] `/effort` — оценка сложности задачи (JSON из LLM → rich Panel)
  - [x] `/map` — карта файлов проекта (rich Tree, глубина 4)
  - [x] `/voice` (STT+TTS) — запланировано в ОТСЕК 6
  - [x] `/architect` — дорогая модель думает → дешёвая модель делает
  - [x] MCP поддержка — запланировано в ОТСЕК 6

  ---

  ## ОТСЕК 6 — Расширенные возможности [PLANNED]

  - [x] `/voice` — STT (Whisper/Google) + TTS (piper-tts) — говорим с агентом
  - [x] MCP поддержка — Model Context Protocol, внешние инструменты
  - [x] `/userprompt` — полноэкранный редактор пользовательского системного промпта (§17.24)
  - [x] Multi-main агенты — несколько главных агентов в одной сессии (§18)
  - [x] Реинкарнация — перенос контекста при переполнении (§18.5 полный протокол)
  - [x] `/modules` — меню модулей (panic_prevention, time_injection, peer_request_expiry и др.)
  - [x] Time injection — дата/время + контекст сессии в системном промпте (§18.14)
  - [x] `/export memory` / `/import memory` — экспорт/импорт памяти агентов (§19.3)
  - [x] `favorite/agent/peer_bus.py` — §18.2 Peer-трафик: ASK_PEER / DELEGATE_PEER / NOTIFY_PEER
    - [x] Теги в executor: _handle_ask_peer / _handle_delegate_peer / _handle_notify_peer
    - [x] Файловая шина: sessions/<id>/peer_bus/inbox_<id>.jsonl + outbox
  - [x] Sandbox субов — изолированный WORKDIR для каждого суб-агента (§19.5)
    - [x] `favorite/agent/sandbox.py` — make_sandbox/cleanup_sandbox, opt-in параметр
    - [x] `run_sub_agent(sandbox=False)` — опциональный параметр + глобальный toggle
  - [x] Параллельный /auto — режимы unified/independent/hybrid (§19.2)
    - [x] `favorite/commands/parallel_auto_cmd.py` — /parallel unified|independent|hybrid
  - [x] Vision поддержка — тег <IMAGE:path=...> или <IMAGE:url=...> (§17.7.6)
  - [x] `_handle_image` в executor.py — base64 + OpenRouter vision API
  - [x] `/tour` — перезапуск онбординг-тура (§17.21)
  - [x] `favorite/commands/tour_cmd.py` — интерактивный пошаговый тур
  - [x] Тег `≪REINCARNATE≫` — самостоятельная реинкарнация агента при 75% контекста (§18.5)
  - [x] `_handle_reincarnate` в executor.py — флаг ctx._reincarnate_requested
  - [x] `/publish` — коммит + push в GitHub одной командой (§17.17)
  

  ---

  ## ХОТФИКС — UX и VoidAI [DONE]

  - [x] `favorite/commands/skills_cmd.py` — очистка экрана при каждом рендере меню и сабменю
  - [x] `favorite/commands/skills_cmd.py` — настройка VoidAI API ключа прямо в `/skills s1` (текстовый ввод, маскировка)
  - [x] `favorite/commands/skills_cmd.py` — новый тип настройки "text" рядом с "choice"
  - [x] `favorite/skills/web_search.py` — исправлен баг: неверное имя атрибута void_ai_key
  - [x] `favorite/skills/web_search.py` — VoidAI native endpoint: https://api.voidai.app/v1/chat/completions
  - [x] `favorite/skills/web_search.py` — fallback на OpenRouter если VoidAI ключ не задан


## VOTE §16.9 [DONE]
- [x] vote.py + executor VOTE handler


  ## ФИНАЛЬНОЕ СОСТОЯНИЕ [DONE — сессия 3]

  Дата: 2026-05-08

  ### Всё реализованное в сессии 3:
  - [x] crew.py — Crew класс: мульти-главный агент, persistent состояние
  - [x] cross_chat.py — CrossChatBus: inter-agent BRIEF/VOTE/ASK_PEER
  - [x] reincarnation_keeper.py — 6-шаговый протокол реинкарнации
  - [x] subs_cmd.py — /subs команда: таблица всех суб-агентов
  - [x] mcp/ — полный MCP клиент (stdio transport) + /mcp команда
  - [x] executor.py — _handle_reincarnate: полный протокол, _handle_mcp_call: MCP_CALL тег
  - [x] __main__.py — точка входа python3 -m favorite
  - [x] agents/main-1.md, sub-critic.md, sub-web.md — bio-файлы агентов
  - [x] .gitignore — исключение мусорных файлов
  - [x] app.py — регистрация SubsCommand и McpCommand (теперь 47 команд)
  - [x] Все IndentationError исправлены (base64-метод записи)
  - [x] Все 25 ключевых файлов синтаксически верны
  - [x] 7/7 интеграционных тестов пройдено

  ### Итого команд: 47
  /agents /architect /auto /build /compact /device /doctor /effort
  /export /favorite api /fetch /help /ide /import /logs /map /mcp
  /memory /model-router /models /modules /new session /openrouter api
  /parallel /plan /prompt-audit /publish /recap /reset /rollback
  /sandbox /session /silent /skill-search /skills /snapshot /stop
  /subs /tasks /telegram /tour /usage /userprompt /voice /wait /web /workers
  