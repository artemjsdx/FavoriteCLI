# hooks skill

  Lifecycle-хуки — shell-скрипты, запускающиеся на события агента.

  ## События: on_message | on_done | on_push | on_error | on_session_start | on_session_end

  ## Конфигурация: config/hooks.json

  ```json
  {"on_done": ["notify-send 'Favorite' 'Задача выполнена!'"]}
  ```

  ## Использование

  ```
  <SKILL:name=hooks>list</SKILL>
  <SKILL:name=hooks>fire:on_done</SKILL>
  ```
  