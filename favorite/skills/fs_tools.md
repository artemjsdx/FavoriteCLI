# fs_tools

  Чтение и запись файлов в пределах рабочей директории (WORKDIR).

  ## Вызов

  ```
  <SKILL:name=fs_tools>read:path=src/main.py</SKILL>
  <SKILL:name=fs_tools>write:path=notes.txt:content=текст заметки</SKILL>
  <SKILL:name=fs_tools>list:path=src/</SKILL>
  ```

  ## Операции

  - `read` — прочитать файл (до 8000 символов)
  - `write` — перезаписать файл
  - `append` — дописать в конец файла
  - `list` — список файлов в папке
  