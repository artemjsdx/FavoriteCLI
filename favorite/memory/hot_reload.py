import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FavoriteMdHandler(FileSystemEventHandler):
  def __init__(self, file_path, callback):
      self.file_path = Path(file_path).resolve()
      self.callback = callback
      self._last_trigger = 0

  def on_modified(self, event):
      if Path(event.src_path).resolve() == self.file_path:
      # Debounce: watchdog sometimes triggers multiple events for one save
          now = time.time()
          if now - self._last_trigger > 0.5:
              self.callback()
              self._last_trigger = now

def start_watcher(path: str, callback) -> Observer:
  path_obj = Path(path).resolve()
  if not path_obj.exists():
    # Create it if it doesn't exist, so we can watch it
    path_obj.touch()
    
  event_handler = FavoriteMdHandler(path_obj, callback)
  observer = Observer()
  # Watch the parent directory because watching a single file can be unreliable on some platforms
  observer.schedule(event_handler, str(path_obj.parent), recursive=False)
  observer.start()
  return observer
