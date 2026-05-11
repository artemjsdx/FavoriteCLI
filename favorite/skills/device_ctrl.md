# device_ctrl — управление Android через ADB

  Скилл для управления вторым Android-устройством (телефоном) через ADB over WiFi.
  Агент может видеть экран, нажимать кнопки, вводить текст, делать свайпы.

  ## Вызов через тег SKILL

  ```
  <SKILL:name=device_ctrl>screenshot</SKILL>
  <SKILL:name=device_ctrl>screenshot:find=кнопка входа</SKILL>
  <SKILL:name=device_ctrl>tap:x=540:y=960</SKILL>
  <SKILL:name=device_ctrl>tap_text:text=Войти</SKILL>
  <SKILL:name=device_ctrl>type:text=user@example.com</SKILL>
  <SKILL:name=device_ctrl>swipe:x1=300:y1=800:x2=300:y2=300:ms=300</SKILL>
  <SKILL:name=device_ctrl>press:key=back</SKILL>
  <SKILL:name=device_ctrl>wait:ms=1500</SKILL>
  <SKILL:name=device_ctrl>ui_dump</SKILL>
  <SKILL:name=device_ctrl>find:text=Создать:action=tap</SKILL>
  <SKILL:name=device_ctrl>launch:pkg=com.google.android.gm</SKILL>
  <SKILL:name=device_ctrl>apps</SKILL>
  <SKILL:name=device_ctrl>device_info</SKILL>
  <SKILL:name=device_ctrl>adb_status</SKILL>
  ```

  ## Прямые теги (executor.py)

  Агент может использовать теги напрямую без SKILL обёртки:
  - `<SCREENSHOT/>` или `<SCREENSHOT find="текст"/>`
  - `<TAP x="540" y="960"/>`
  - `<TAP_TEXT text="Войти"/>`
  - `<TYPE text="hello@gmail.com"/>`
  - `<TYPE_CLEAR text="новый текст"/>`
  - `<SWIPE x1="300" y1="800" x2="300" y2="300" ms="300"/>`
  - `<PRESS key="back"/>`
  - `<WAIT ms="1500"/>`
  - `<UI_DUMP/>`
  - `<FIND_ELEMENT text="ОК" action="tap"/>`
  - `<APP_LAUNCH pkg="com.google.android.gm"/>`
  - `<APP_LIST/>`
  - `<DEVICE_INFO/>`
  - `<ADB_STATUS/>`

  ## Vision loop
  После каждого SCREENSHOT агент получает JSON:
  {"description": "...", "found": true/false, "x": N, "y": N, "suggested_action": "..."}
  