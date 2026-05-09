# web_panel skill

  Запускает локальный веб-дашборд (FastAPI) для мониторинга сессий, задач и логов FavoriteCLI.

  ## Требования

  ```bash
  pip install fastapi uvicorn
  ```

  ## Использование

  ```
  <SKILL:name=web_panel>start</SKILL>   — запустить на http://localhost:7860
  <SKILL:name=web_panel>stop</SKILL>   — остановить
  <SKILL:name=web_panel>status</SKILL> — статус
  ```

  ## Порт

  По умолчанию: **7860**. Можно изменить через переменную окружения `FAV_PANEL_PORT`.

  ## Возможности

  - Список всех сессий с количеством сообщений
  - Просмотр истории диалога каждой сессии
  - Просмотр плана сессии
  - REST API: `/api/sessions`, `/api/health`
  