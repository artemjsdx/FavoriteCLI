from pathlib import Path

_DEFAULT = Path(__file__).resolve().parent.parent.parent / "Favorite.md"


class FavoriteMd:
  def __init__(self, path: Path = _DEFAULT):
      self._path = path

  def read(self) -> str:
      if not self._path.exists():
          return ""
      return self._path.read_text(encoding="utf-8")

  def write(self, content: str) -> None:
      self._path.write_text(content, encoding="utf-8")

  def append_section(self, section: str) -> None:
      current = self.read()
      self.write(current + "\n\n" + section)
