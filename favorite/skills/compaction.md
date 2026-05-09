# compaction skill

  Сжимает длинную историю диалога в краткое резюме для экономии токенов.

  ## Использование

  ```
  <SKILL:name=compaction>max_messages=50</SKILL>
  ```

  Сохраняет результат в `sessions/<id>/context_summary.md` — автоматически вшивается в следующий системный промпт.
  