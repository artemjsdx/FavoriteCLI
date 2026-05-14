"""
favorite/skills/device_ctrl/ui_dump.py — парсинг XML UI dump от uiautomator.
FIX-3: max_items увеличен до 50, добавлены text-only элементы, dump_summary_full().
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


def find_all_text_nodes(xml_str: str) -> list[dict]:
    """FIX-3: Возвращает ВСЕ узлы с текстом (не только clickable)."""
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []
    results = []
    seen_texts = set()
    for node in root.iter():
        text = (node.get("text", "") or node.get("content-desc", "")).strip()
        if text and text not in seen_texts:
            seen_texts.add(text)
            bounds = node.get("bounds", "")
            c = _bounds_center(bounds) if bounds else None
            clickable = node.get("clickable") == "true"
            results.append({
                "text": text,
                "x": c[0] if c else None,
                "y": c[1] if c else None,
                "clickable": clickable,
                "class": node.get("class", ""),
            })
    return results


def get_package_name(xml_str: str) -> str:
    """FIX-3: Определяет пакет верхнего окна из XML."""
    try:
        root = ET.fromstring(xml_str)
        # Ищем атрибут package у корневого узла или первого child
        pkg = root.get("package", "")
        if not pkg:
            for child in root:
                pkg = child.get("package", "")
                if pkg:
                    break
        return pkg or "unknown"
    except ET.ParseError:
        return "parse_error"


def dump_summary(xml_str: str, max_items: int = 50) -> str:
    """FIX-3: Увеличен лимит до 50, добавлены текстовые узлы и имя пакета."""
    pkg = get_package_name(xml_str)
    clickable = find_all_clickable(xml_str)
    all_text = find_all_text_nodes(xml_str)

    lines = [f"[Пакет: {pkg}]"]

    if not clickable and not all_text:
        return "[UI dump: элементов не найдено]\n" + lines[0]

    # Кликабельные элементы
    if clickable:
        lines.append(f"\nКликабельные элементы ({len(clickable)}):")
        for it in clickable[:max_items]:
            lines.append(f"  TAP [{it[x]},{it[y]}] {it[text][:60]}")

    # Текстовые элементы (не кликабельные) — контент экрана
    text_only = [t for t in all_text if not t["clickable"] and t["text"] not in
                 {c["text"] for c in clickable}]
    if text_only:
        lines.append(f"\nТекст на экране ({len(text_only)}):")
        for it in text_only[:30]:
            coord = f"[{it[x]},{it[y]}] " if it["x"] is not None else ""
            lines.append(f"  TXT {coord}{it[text][:60]}")

    return "\n".join(lines)


def dump_summary_full(xml_str: str, max_chars: int = 6000) -> str:
    """FIX-3: Возвращает сырой XML (обрезанный) для глубокого анализа агентом."""
    pkg = get_package_name(xml_str)
    header = f"[Пакет: {pkg}] [RAW XML, первые {max_chars} символов]\n"
    if len(xml_str) > max_chars:
        return header + xml_str[:max_chars] + "\n...[TRUNCATED]"
    return header + xml_str
