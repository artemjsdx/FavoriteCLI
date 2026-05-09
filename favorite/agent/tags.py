"""
Tag parser for FavoriteCLI.

Supported formats (all equivalent):
<TAG:args>body</TAG>          ← preferred, simple ASCII
«TAG:args»body«/TAG»          ← guillemet variant (U+00AB/BB)
≪TAG:args≫body≪/TAG≫          ← heavy guillemet (U+226A/226B)
<<TAG:args>>body<</TAG>>      ← ASCII double-angle

Inline (no body): <TAG:args>  «TAG:args»  ≪TAG:args≫  <<TAG:args>>
Closing tags:     </TAG>  «/TAG»  ≪/TAG≫  <</TAG>>

<tool_call> wrappers are stripped before parsing.
"""
import re
from dataclasses import dataclass

TAG_OPEN  = "<"
TAG_CLOSE = ">"

# ── Guillemet-style open/close ──────────────────────────────────
_GO = r"(?:≪|«|<<)"
_GC = r"(?:≫|»|>>)"

# ── Any closing tag variant ──────────────────────────────────────
# matches: </TAG>  «/TAG»  ≪/TAG≫  <</TAG>>
def _any_close(group_ref: str) -> str:
  return rf"(?:</{group_ref}>|{_GO}/{group_ref}{_GC})"

# ── Block regexes ────────────────────────────────────────────────
# 1) HTML-style:  <TAG:args>body</TAG>   (uppercase names only to avoid HTML noise)
BLOCK_HTML_RE = re.compile(
  r"<([A-Z][A-Z0-9_]*)([^>]*)>(.+?)</\1>",
  re.DOTALL,
)
# 2) Guillemet-style open + any close: «TAG:args»body</TAG> etc.
BLOCK_GUILD_RE = re.compile(
  _GO + r"(\w+)" + r"(?::([^≫»>]*?))?" + _GC
  + r"(.*?)"
  + _any_close(r"\1"),
  re.DOTALL,
)

# ── Inline regexes ───────────────────────────────────────────────
# HTML-style inline: <TAG:args>  (uppercase, not immediately followed by content+close)
INLINE_HTML_RE = re.compile(
  r"<([A-Z][A-Z0-9_]*)([^>]*)>(?!\s*[^<])"
)
# Guillemet-style inline
INLINE_GUILD_RE = re.compile(
  _GO + r"(\w+)" + r"(?::([^≫»>]*?))?" + _GC
)

# ── Wrapper stripping ────────────────────────────────────────────
_TOOL_CALL_RE     = re.compile(r"<tool_call>\s*",   re.IGNORECASE)
_TOOL_CALL_END_RE = re.compile(r"\s*</tool_call>",  re.IGNORECASE)


@dataclass
class ParsedTag:
  name: str
  args: dict[str, str]
  body: str | None
  span: tuple[int, int]


def _parse_args(raw: str | None) -> dict[str, str]:
    """
    Auto-detects TWO tag-arg formats:
      HTML-attr style: server="name" tool="t"   (LLM-natural, space-separated)
      Colon style:     :server=name:tool=t       (legacy)
    This makes MCP_CALL / REINCARNATE tags work regardless of LLM output style.
    Treatment: fixes the entire class of 'LLM generates HTML-attr, parser ignores it'.
    """
    if not raw:
        return {}
    stripped = raw.strip()
    if not stripped:
        return {}
    result: dict[str, str] = {}
    # Colon format (§20.2): starts with ':' OR contains ':key=' (e.g. name=myjob:cmd=ls)
    import re as _re2
    if stripped.startswith(':') or _re2.search(r':\w+=', stripped):
        for part in stripped.lstrip(':').split(':'):
            part = part.strip()
            if '=' in part:
                k, _, v = part.partition('=')
                result[k.strip()] = v.strip().strip('"').strip("'")
        return result
    # HTML-attr format: key="value" key='value' or key=bare (LLM-natural)
    _attr_re = _re2.compile(r'(\w+)\s*=\s*(?:"([^"]*?)"|' + r"'([^']*?)'|([^\s>]*))")
    matches = list(_attr_re.finditer(stripped))
    if matches:
        for m in matches:
            key = m.group(1)
            val = next((g for g in (m.group(2), m.group(3), m.group(4)) if g is not None), '')
            result[key] = val
        return result
    return result


def _preprocess(text: str) -> str:
  text = _TOOL_CALL_RE.sub("", text)
  text = _TOOL_CALL_END_RE.sub("", text)
  return text


def _code_block_spans(text: str) -> list[tuple[int, int]]:
  """Return (start, end) spans of fenced code blocks and inline code — tags inside them are not executed."""
  spans: list[tuple[int, int]] = []
  # Fenced blocks: ```...``` (possibly with language hint)
  for m in re.finditer(r'```[\w]*\n?.*?```', text, re.DOTALL):
      spans.append((m.start(), m.end()))
  # Inline code: `...` (single-line only)
  for m in re.finditer(r'`[^`\n]+`', text):
      spans.append((m.start(), m.end()))
  return spans


def _in_code(span: tuple[int, int], code_spans: list[tuple[int, int]]) -> bool:
  return any(cs <= span[0] and span[1] <= ce for cs, ce in code_spans)


def extract_tags(text: str) -> list[ParsedTag]:
  text = _preprocess(text)
  code_spans = _code_block_spans(text)
  tags: list[ParsedTag] = []
  consumed: set[tuple[int, int]] = set()

  # ── Block: HTML-style ──
  for m in BLOCK_HTML_RE.finditer(text):
      span = (m.start(), m.end())
      if _in_code(span, code_spans):
          continue
      pt = ParsedTag(
          name=m.group(1),
          args=_parse_args(m.group(2)),
          body=m.group(3).strip(),
          span=span,
      )
      tags.append(pt)
      consumed.add(span)

  # ── Block: guillemet-style ──
  for m in BLOCK_GUILD_RE.finditer(text):
      span = (m.start(), m.end())
      if any(s <= span[0] < e for s, e in consumed):
          continue
      if _in_code(span, code_spans):
          continue
      pt = ParsedTag(
          name=m.group(1),
          args=_parse_args(m.group(2)),
          body=m.group(3).strip(),
          span=span,
      )
      tags.append(pt)
      consumed.add(span)

  # ── Inline: guillemet-style ──
  for m in INLINE_GUILD_RE.finditer(text):
      span = (m.start(), m.end())
      if any(s <= span[0] < e for s, e in consumed):
          continue
      if _in_code(span, code_spans):
          continue
      name = m.group(1)
      if name.startswith("/"):
          continue
      tags.append(ParsedTag(
          name=name,
          args=_parse_args(m.group(2)),
          body=None,
          span=span,
      ))

  # ── Inline: HTML-style (uppercase only) ──
  for m in INLINE_HTML_RE.finditer(text):
      span = (m.start(), m.end())
      if any(s <= span[0] < e for s, e in consumed):
          continue
      if _in_code(span, code_spans):
          continue
      name = m.group(1)
      tags.append(ParsedTag(
          name=name,
          args=_parse_args(m.group(2)),
          body=None,
          span=span,
      ))

  tags.sort(key=lambda t: t.span[0])
  return tags


def strip_tags(text: str) -> str:
  text = _preprocess(text)
  result = BLOCK_HTML_RE.sub("", text)
  result = BLOCK_GUILD_RE.sub("", result)
  result = INLINE_GUILD_RE.sub("", result)
  result = INLINE_HTML_RE.sub("", result)
  return result.strip()
