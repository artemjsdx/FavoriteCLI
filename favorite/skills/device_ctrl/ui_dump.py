"""
  favorite/skills/device_ctrl/ui_dump.py — парсинг XML UI dump от uiautomator.
  """
  import xml.etree.ElementTree as ET
  import re


  def _bounds_center(bounds_str: str) -> tuple[int, int] | None:
      m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
      if not m:
          return None
      x1, y1, x2, y2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
      return (x1 + x2) // 2, (y1 + y2) // 2


  def find_by_text(xml_str: str, text: str) -> tuple[int, int] | None:
      try:
          root = ET.fromstring(xml_str)
      except ET.ParseError:
          return None
      text_lower = text.lower()
      for node in root.iter():
          node_text = node.get("text", "") or node.get("content-desc", "")
          if text_lower in node_text.lower():
              bounds = node.get("bounds", "")
              if bounds:
                  return _bounds_center(bounds)
      return None


  def find_by_class(xml_str: str, class_name: str) -> list[tuple[int, int]]:
      try:
          root = ET.fromstring(xml_str)
      except ET.ParseError:
          return []
      results = []
      for node in root.iter():
          if class_name.lower() in (node.get("class") or "").lower():
              bounds = node.get("bounds", "")
              c = _bounds_center(bounds)
              if c:
                  results.append(c)
      return results


  def find_all_clickable(xml_str: str) -> list[dict]:
      try:
          root = ET.fromstring(xml_str)
      except ET.ParseError:
          return []
      results = []
      for node in root.iter():
          if node.get("clickable") == "true":
              text = node.get("text", "") or node.get("content-desc", "")
              bounds = node.get("bounds", "")
              c = _bounds_center(bounds)
              if c and text:
                  results.append({"text": text, "x": c[0], "y": c[1], "class": node.get("class", "")})
      return results


  def dump_summary(xml_str: str, max_items: int = 20) -> str:
      items = find_all_clickable(xml_str)
      if not items:
          return "[UI dump: кликабельных элементов не найдено]"
      lines = [f"Кликабельные элементы ({len(items)}):"]
      for it in items[:max_items]:
          lines.append(f"  [{it['x']},{it['y']}] {it['text'][:50]}")
      return "\n".join(lines)
  