from prompt_toolkit.styles import Style

STYLE = Style.from_dict({
  # Промпт
  "prompt-arrow":   "#ffffff bold",

  # Completion menu — тёмный фон, белый текст, оранжевый выбор
  "completion-menu":                        "bg:#1a1a1a #cccccc",
  "completion-menu.completion":             "bg:#1a1a1a #cccccc",
  "completion-menu.completion.current":     "bg:#2a1800 #ff8c00 bold",
  "completion-menu.meta.completion":        "bg:#111111 #666666",
  "completion-menu.meta.completion.current":"bg:#2a1800 #ff8c00",
  "scrollbar.background":                   "bg:#222222",
  "scrollbar.button":                       "bg:#ff8c00",

  # Остальные элементы
  "frame":          "#ff8c00",
  "frame-title":    "#ff8c00 bold",
  "agent-dot":      "#ff8c00 bold",
  "step-prefix":    "#888888",
  "step-text":      "#aaaaaa",
  "thinking":       "#888888 italic",
  "slash-match":    "#ff8c00 bold",
  "slash-item":     "#cccccc",
  "status-bar":     "bg:#1a1a1a #666666",
  "header-orange":  "#ff8c00",
  "header-white":   "#ffffff",
  "dim":            "#666666",
  "error":          "#ff4444",
  "warn":           "#ffaa00",
  "ok":             "#44ff88",
  "separator":      "#333333",
})

ORANGE  = "#ff8c00"
WHITE   = "#ffffff"
GRAY    = "#888888"
DIM     = "#555555"
RED     = "#ff4444"
GREEN   = "#44ff88"
YELLOW  = "#ffaa00"

# Шрифт баннера — менять здесь
# Протестированные варианты (все влезают в 50 символов):
#   "small"       — 37 ширина, 4 строки, чистый (дефолт)
#   "small_slant" — 42 ширина, 4 строки, наклонный
#   "mini"        — 30 ширина, 3 строки, компактный
LOGO_FONT = "small"
