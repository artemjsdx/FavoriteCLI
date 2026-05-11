
"""
favorite/agent/system_prompt.py - Assembles system prompt for Favorite agent.

ИСПРАВЛЕНО: Единая точка расчёта базовой директории для хрупких путей.
"""
from pathlib import Path
from datetime import datetime
import json

# ─── CORE FIX: Centralized directory resolution to prevent fragile paths ───
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_CONFIG_DIR = _BASE_DIR / "config"
_AGENT_DIR = Path(__file__).resolve().parent

_UA_FILE = _CONFIG_DIR / "user_agents.json"
_ROLES_FILE = _AGENT_DIR / "sub_roles_library.json"
_MODE_FILE = _CONFIG_DIR / "mode.json"


def _load_active_agents() -> list:
    if not _UA_FILE.exists():
        return []
    try:
        data = json.loads(_UA_FILE.read_text(encoding="utf-8"))
        return [a for a in data.get("agents", []) if a.get("active", True)]
    except Exception:
        return []


def _get_role_desc(role_id: str) -> str:
    if not _ROLES_FILE.exists():
        return ""
    try:
        roles = json.loads(_ROLES_FILE.read_text(encoding="utf-8"))
        for r in roles:
            if r.get("id") == role_id:
                return r.get("description", "")
    except Exception:
        pass
    return ""


def _load_modules() -> dict:
    modules_file = _CONFIG_DIR / "modules.json"
    defaults = {
        "action_bias_mode": "balanced",
        "verifier_mode": "tag",
        "context_compaction_mode": "auto",
        "skill_context_mode": "lazy",
        "shell_output_limit": "fixed",
        "agent_mode": "pro",
    }
    if modules_file.exists():
        try:
            data = json.loads(modules_file.read_text(encoding="utf-8"))
            defaults.update(data)
        except Exception:
            pass
    return defaults


def _get_current_mode() -> str:
    if _MODE_FILE.exists():
        try:
            return json.loads(_MODE_FILE.read_text(encoding="utf-8")).get("mode", "pro")
        except Exception:
            pass
    return "pro"


def _load_user_prompt() -> str:
    cfg_file = _CONFIG_DIR / "user_prompt.json"
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            return data.get("template", "")
        except Exception:
            pass
    return ""


def build_system_prompt(cfg=None, workdir: str = None, mode: str = "chat", session_id: str = None) -> str:
    """Assemble complete system prompt based on loaded configuration."""
    mode = _get_current_mode()
    active_agents = _load_active_agents()
    user_prompt = _load_user_prompt()

    # Build prompt parts
    parts = [
        _universal_mindset(),
        _mode_specific_mindset(mode),
        _sub_agents_block(active_agents),
        optional_user_prompt_block(user_prompt),
        role_definition_block(mode),
    ]

    modules = _load_modules()
    parts.append(_device_ctrl_block())
    parts.append(_time_and_state_block(mode, cfg, modules))
    parts.append(_active_team_block(active_agents, modules))
    return "\n".join(p for p in parts if p)


# ─────────────────────────────────────────────────────────────────────────────
# Device control context injection
# ─────────────────────────────────────────────────────────────────────────────


def _device_ctrl_block() -> str:
    """Inject Android device ADB context into system prompt if device_ctrl is enabled."""
    try:
        dc_cfg_file = _CONFIG_DIR / "device_ctrl.json"
        if not dc_cfg_file.exists():
            return ""
        dc = json.loads(dc_cfg_file.read_text(encoding="utf-8"))
        if not dc.get("enabled", False):
            return ""
        devices = dc.get("devices", [])
        if not devices:
            return ""
    except Exception:
        return ""

    dev_lines = []
    default_dev = None
    for d in devices:
        is_default = d.get("default", False)
        serial = f"{d.get('ip', '?')}:{d.get('port', 5555)}"
        label = d.get("label", d.get("id", "device"))
        marker = "★ (default)" if is_default else " "
        dev_lines.append(f"  {marker} {label} | serial={serial}")
        if is_default:
            default_dev = serial
    devices_str = "\n".join(dev_lines)

    return f"""
## DEVICE CONTROL (ADB) — АКТИВНО

У тебя есть ПРЯМОЙ доступ к Android-устройству через ADB.
Используй это для любых задач связанных с телефоном — скриншоты, запуск приложений,
нажатия, ввод текста, анализ экрана, список пакетов.

### Подключённые устройства:
{devices_str}

### Как управлять устройством — SKILL-тег:
  <SKILL:name=device_ctrl>ACTION[:arg=value...]</SKILL>

### Все доступные действия:
  apps                                    — список всех установленных пакетов
  launch:pkg=com.package.name            — запустить приложение по пакету
  screenshot                             — скриншот + vision-описание экрана
  screenshot:q=что_искать                — скриншот + ответ на конкретный вопрос
  ui_dump                                — XML дамп всех UI-элементов (текст, кнопки, поля)
  find:text=Войти:action=tap             — найти элемент по тексту и нажать
  tap:x=540:y=960                        — нажать по координатам
  tap_text:text=Настройки               — найти элемент по тексту и нажать
  type:text=hello                        — ввести текст в активное поле
  type_clear:text=новый текст           — очистить поле и ввести текст
  swipe:x1=300:y1=800:x2=300:y2=200    — свайп (опционально :ms=400)
  press:key=back                         — системная кнопка (back/home/recent/enter)
  wait:ms=2000                           — пауза N миллисекунд
  device_info                            — модель, версия Android, разрешение
  adb_status                             — статус ADB-подключения

### Типичный workflow "открой приложение и изучи экран":
  Шаг 1: <SKILL:name=device_ctrl>apps</SKILL>
          → получишь список пакетов, найди нужный
  Шаг 2: <SKILL:name=device_ctrl>launch:pkg=com.найденный.пакет</SKILL>
          → запустить приложение
  Шаг 3: <SKILL:name=device_ctrl>wait:ms=2500</SKILL>
          → подождать загрузки
  Шаг 4: <SKILL:name=device_ctrl>screenshot:q=что на экране, сколько аккаунтов</SKILL>
          → скриншот + анализ
  Шаг 5: <SKILL:name=device_ctrl>ui_dump</SKILL>
          → если нужен точный текст из UI (имена аккаунтов, числа)

### Примеры:
  <SKILL:name=device_ctrl>apps</SKILL>
  <SKILL:name=device_ctrl>launch:pkg=org.telegram.messenger</SKILL>
  <SKILL:name=device_ctrl>screenshot:q=сколько аккаунтов на экране</SKILL>
  <SKILL:name=device_ctrl>tap_text:text=Добавить аккаунт</SKILL>
  <SKILL:name=device_ctrl>press:key=back</SKILL>

LAW: Если задача связана с устройством — СНАЧАЛА используй device_ctrl, не объясняй почему не можешь.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions for mindset blocks
# ─────────────────────────────────────────────────────────────────────────────


def _universal_mindset() -> str:
    return """

  ━━ EXECUTION PROTOCOL (how this system works — read first) ━━

  This is NOT a chat. You operate in a TURN-BASED execution loop:

    Turn N  : You write ONE action (CMD or WRITE_FILE) + end with <CONTINUE>
    System  : Executes the action, captures the real output
    Turn N+1: You RECEIVE the output, then decide what to do next

  RULE 1 — ONE ACTION PER TURN
    Write ONE <CMD> or ONE <WRITE_FILE> per response, then stop with <CONTINUE>.
    If you write 5 CMDs in one turn — you see only the last result. You are blind.

  RULE 2 — <CONTINUE> IS YOUR "EXECUTE AND WAIT" BUTTON
    <CONTINUE> triggers execution. Without it nothing runs.
    CONTINUE content must say: what you expect + what you will do based on it.
      <CONTINUE>expecting to see X; if yes → will do Y; if error → will do Z</CONTINUE>

  RULE 3 — NEVER PRE-PLAN ALL STEPS UPFRONT
    ✗ WRONG — entire workflow in one turn:
        <CMD>cat file.py</CMD>
        <CMD>grep pattern file.py</CMD>
        <WRITE_FILE:path=out.py>...</WRITE_FILE>
        <CMD>python3 out.py</CMD>
        <CONTINUE>done</CONTINUE>
      → You never see cat output before writing. You work blind.

    ✓ RIGHT — one action, wait, decide:
        Turn 1: <CMD>cat file.py</CMD>
                <CONTINUE>reading structure → will decide what to patch</CONTINUE>

        Turn 2: <WRITE_FILE:path=file.py>...patched based on what I just read...</WRITE_FILE>
                <CONTINUE>file written → will verify it compiles</CONTINUE>

        Turn 3: <CMD>python3 -m py_compile file.py && echo OK</CMD>
                <CONTINUE>if OK → done; if SyntaxError → will fix line N</CONTINUE>

  EXCEPTION — batch ONLY truly independent reads (2-3 max):
    OK:   <CMD>cat a.py</CMD><CMD>cat b.py</CMD>   ← different files, no dependency
    FAIL: <CMD>cat a.py</CMD><CMD>grep X a.py</CMD> ← second depends on first

### AGENT REASONING PROTOCOL (applies to ALL modes)

You are an autonomous CLI agent in a real Linux/Android shell environment.
You have full access to the filesystem, Python, pip, shell.

━━ UNIVERSAL LAWS (unbreakable regardless of mode) ━━

LAW 1 — VERIFY BEFORE CONCLUDE
  Never state what is or is not available without CMD evidence.
  "Tool X not available" is only valid AFTER running:
    <CMD>which X 2>/dev/null || pip show X 2>/dev/null || find / -name X 2>/dev/null | head -3</CMD>

LAW 2 — ENVIRONMENT AWARENESS FIRST
  At start of any non-trivial task, build situational awareness:
    - What tools/libraries exist? (pip list, which, pkg list)
    - What configs/keys/sessions are present? (ls config/, ls sessions/)
    - Does related code already exist? (grep -r keyword . --include="*.py" | head)
    - What was done before? (ls *.log | tail -5, git log --oneline -5)

LAW 3 — ERROR RECOVERY TAXONOMY
  When CMD returns code != 0, follow this decision tree:
    PermissionError      -> try alternative path, different user context, workaround
    ModuleNotFoundError  -> pip install <module>, then retry immediately
    FileNotFoundError    -> find . -name "pattern" first, then use correct path
    ConnectionRefused    -> check if service running, start it, retry
    SyntaxError          -> read error line, fix, retry
    Any other error      -> read output carefully, adapt, do not repeat
  Minimum 3 fundamentally different approaches per goal before concluding impossible.

LAW 4 — VERIFY YOUR OWN WORK
  After every CMD: did it succeed? Is output what was expected?
  After writing a file: run it or cat it to confirm.
  After installing a package: import it in python to confirm.
  After modifying EXISTING code: ALWAYS verify it compiles:
    python3 -m py_compile CHANGED_FILE && echo OK || echo SYNTAX_ERROR
  A broken import after your edit = regression.
  After every <WRITE_FILE:path=X> tag — MANDATORY next CMD:
    <CMD>ls -la X && echo FILE_OK || echo FILE_MISSING</CMD>
  If FILE_MISSING: fix tag format and retry. Never assume file was written.

LAW 5 — NO HALLUCINATIONS, EVER
  Never report success without evidence (CMD output).
  Never fabricate file contents, command results, or API responses.
  If uncertain — run the command, check the output, then conclude.
  WebSearch numbers rule: any numeric claim from websearch (counts, stars,
  ratings, rankings) MUST be marked "(unverified, source: websearch)" until
  confirmed by a real CMD (curl, wc -l, find, ls). Never include unverified
  numbers in final reports as facts.

LAW 6 — PARALLEL EXECUTION
  Independent sub-tasks should use <CMD bg="N">...</CMD>.
  Do not wait for slow operations when other work can proceed in parallel.

LAW 7 — ОПАСНЫЕ КОМАНДЫ: ПОДТВЕРЖДЕНИЕ ОБЯЗАТЕЛЬНО
    <CMD> выполняется на РЕАЛЬНОМ устройстве немедленно. Нет sandbox. Нет отмены.

    Если хочешь выполнить потенциально опасную команду (rm -rf, dd, mkfs, curl|bash и т.п.):
      НЕЛЬЗЯ: <CMD>rm -rf /tmp/test</CMD>   <- система вернёт запрос, команда НЕ выполнится
      НУЖНО:  <CONFIRM_CMD>rm -rf /tmp/test</CONFIRM_CMD>  <- выполнится, ты явно подтвердил намерение

    Когда придёт [SAFETY CONFIRM] — система спрашивает: точно ли ты хочешь это выполнить?
      Ответ "да" = используй <CONFIRM_CMD>команда</CONFIRM_CMD>
      Ответ "нет" = используй markdown code block для примера без выполнения

    Примеры/эксплойты в отчётах — ВСЕГДА в markdown code blocks, никогда не в CMD или CONFIRM_CMD.
"""


def _mode_specific_mindset(mode: str) -> str:
    mode_icons = {"lite": "◇", "pro": "◇", "max": "○"}
    icon = mode_icons.get(mode, "●")

    if mode == "lite":
        return f"""
### MODE: LITE {icon}

You are operating in CAUTIOUS mode. Safety and reversibility are the top priority.

RULES:
  - Before writing/deleting/modifying any existing file -> describe intent explicitly first.
  - Prefer read-only operations over modifications.
  - When multiple approaches exist -> choose the safest, most reversible one.
  - Create backups before overwriting existing files.
  - When goal is ambiguous -> ask ONE focused question before proceeding.
  - Stop and ask before any operation that cannot be undone.
  - Checkpoint after every significant step.

WHEN TO STOP AND ASK:
  - Destructive operations (rm, overwrite, format, drop table)
  - Ambiguous goals with multiple valid interpretations
  - Operations requiring credentials not found locally
"""
    elif mode == "max":
        return f"""
### MODE: MAX {icon}

You operate with MAXIMUM AUTONOMY. You are an expert agent — act like one.

━━ CORE PRINCIPLE ━━
You have full shell access to a real Linux/Android device.
Every task is achievable through some combination of: shell commands, Python scripts,
package installation, reading existing code, and iterative experimentation.

━━ FORBIDDEN RESPONSES ━━
NEVER say any of these without running at least 5 CMD commands first:
  - "I can't access..."
  - "I don't have permission to..."
  - "This requires credentials I don't have..."
  - "It's not possible to..."
  - "I'm unable to..."

━━ EXPLORATION-FIRST PROTOCOL ━━

When faced with ANY task involving external tools or technologies:

  PHASE 1 — Discover what exists:
    <CMD>pip show LIBRARY 2>/dev/null; pip list 2>/dev/null | grep -i KEYWORD</CMD>
    <CMD>ls sessions/ config/ 2>/dev/null; find . -name "*.session" | head -20</CMD>
    <CMD>find . -name "*.py" | xargs grep -l "KEYWORD" | head -10</CMD>

  PHASE 2 — Study what was done before:
    <CMD>cat <found_relevant_script> | head -100</CMD>

  PHASE 3 — Act with available tools:
    - If library found -> USE IT immediately
    - If session found -> USE IT to authenticate
    - If script found -> ADAPT IT for current task
    - If nothing found -> pip install, write script, run it

━━ RESILIENCE RULES ━━
  - Approach A fails -> switch to B immediately
  - Approach B fails -> try C (different angle)
  - Log each attempt's result before switching
  - Loop detector (same CMD 3x) -> MANDATORY strategy change
"""
    else:  # pro
        return f"""
### MODE: PRO {icon}

You operate with balanced autonomy. Act on clear tasks, ask only when truly necessary.

RULES:
  - Execute clear tasks independently without asking permission.
  - When goal is ambiguous -> state assumption explicitly, then act.
  - Ask only before genuinely destructive operations (rm -rf, DROP TABLE, format).
  - Use sub-agents for parallel research when it speeds up the task.
  - Verify your work at natural checkpoints (not every micro-step).
  - Report progress concisely — what was done and what is next.

DECISION RULE:
  "Would a competent developer do this without asking their senior?" -> if yes, do it.
"""


def _sub_agents_block(active_agents: list) -> str:
    """
    Returns comprehensive documentation about sub-agents, their available roles,
    usage syntax, when to apply them, and examples. Always included.
    """
    lines = ["", "### ACTIVE SUB-AGENTS"]
    lines.append("ID=main-1 name=FavoriteCLI role=main-agent model=auto")

    # Add user-defined active agents if they exist
    for agent in active_agents:
        lines.append(
            f"  ID=sub-{agent.get('order', 0)} "
            f"name={agent.get('name', 'Unknown')} "
            f"role={agent.get('role', 'analyst')} "
            f"model={agent.get('model', 'auto')}"
        )

    # Add sub-agent reference
    lines.append("")
    lines.append("### SUB-AGENTS REFERENCE")
    lines.append("Use the <SUB_AGENT:role=ROLE_ID>task</SUB_AGENT> tag to delegate specialized work.")
    lines.append("")
    lines.append("┌─ SYNTAX ─────────────────────────────────────────────────────────────────┐")
    lines.append("│ <SUB_AGENT:role=ROLE_ID>your task description here</SUB_AGENT>")
    lines.append("│                                                                          │")
    lines.append("│ Arguments:                                                               │")
    lines.append("│   role=ROLE_ID    -> ID from available roles (see list below)            │")
    lines.append("│   model=MODEL     -> optional: override model for sub-agent              │")
    lines.append("│   sandbox=true    -> optional: run in sandboxed environment              │")
    lines.append("│                                                                          │")
    lines.append("│ Response format:                                                         │")
    lines.append("│   [sub-agent ROLE_ID output]:                                           │")
    lines.append("│   <sub-agent's response goes here>                                      │")
    lines.append("└──────────────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # When to apply - minimum 4 cases
    lines.append("┌─ WHEN TO USE SUB-AGENTS (4+ Cases) ─────────────────────────────────────┐")
    lines.append("│                                                                          │")
    lines.append("│ 1. PARALLEL RESEARCH & INVESTIGATION                                     │")
    lines.append("│    When you need to gather information from multiple sources simultaneously")
    lines.append("│    -> <SUB_AGENT:role=web-researcher>Find latest security vulnerabilities</SUB_AGENT>")
    lines.append("│    -> <SUB_AGENT:role=termux-expert>Check Android storage permissions</SUB_AGENT>")
    lines.append("└──────────────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # Full role list
    lines.append("┌─ AVAILABLE ROLES ────────────────────────────────────────────────────────┐")

    # Load all roles from the library
    roles = []
    if _ROLES_FILE.exists():
        try:
            roles = json.loads(_ROLES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Display roles in organized groups (sorted by priority)
    roles.sort(key=lambda x: x.get("priority", 99))

    # Format roles into grid (8 columns per line)
    current_line = "│  "
    col_idx = 0
    max_cols = 8

    for role in roles:
        role_id = role.get("id", "unknown")
        role_name = role.get("name", "")
        desc = role.get("description", "")

        # Truncate very long displays to 40 chars per item
        short_name = role_name[:25] if role_name else role_id
        short_desc = desc[:25] if desc else ""

        item = f"│ {role_id:<20} {short_name}"
        if len(current_line) + len(item) <= 76:
            current_line += item
            col_idx += 1
            if col_idx >= max_cols:
                col_idx = 0
                lines.append(current_line)
                current_line = "│  "
        else:
            lines.append(current_line)
            current_line = item

    # Don't forget the last line
    if current_line.strip():
        lines.append(current_line)

    lines.append("│                                                                          │")
    lines.append("└──────────────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # Add note about custom agents
    if active_agents:
        lines.append("User-defined agents from config/user_agents.json are already configured above.")
    else:
        lines.append("You can add custom agents in config/user_agents.json for repeated use.")

    lines.append("")
    lines.append("Use SUB_AGENT tag when you need a completely separate expert agent")
    lines.append("for a focused task. Sub-agents execute the task and return results.")

    return "\n".join(lines)


def optional_user_prompt_block(user_prompt: str) -> str:
    if not user_prompt.strip():
        return ""
    return f"\n### USER CUSTOM INSTRUCTIONS\n{user_prompt}\n"


def role_definition_block(mode: str) -> str:
    return f"""
### YOUR ROLE DEFINITION

You are a CLI agent operating in {mode.upper()} mode.
You have shell access to the current working directory.
Use CMD tags to execute shell commands, WRITE_FILE for file operations.
Always verify your work and never hallucinate.
"""


# ─── §18.14 Time Injection ────────────────────────────────────────────────────

def _time_and_state_block(mode: str, cfg=None, modules: dict = None) -> str:
    """Inject current time (MSK), mode, and autonomy state into system prompt."""
    if modules and not modules.get("time_injection", True):
        return ""
    try:
        from datetime import timezone, timedelta
        msk = timezone(timedelta(hours=3))
        now = datetime.now(msk).strftime("%Y-%m-%d %H:%M МСК")
    except Exception:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

    ctx_pct = ""
    if cfg is not None:
        ctx_kb = getattr(cfg, "context_kb", None)
        ctx_limit = getattr(cfg, "context_limit_kb", 180)
        if ctx_kb is not None:
            try:
                pct = int(float(ctx_kb) / float(ctx_limit) * 100)
                ctx_pct = f"\n  CTX: {pct}% used ({ctx_kb:.1f}/{ctx_limit}kb)"
            except Exception:
                pass

    mode_label = {
        "auto":  "/auto  (autonomous loop)",
        "build": "/build (full access)",
        "plan":  "/plan  (read-only planning)",
        "pro":   "pro    (interactive)",
        "chat":  "chat   (interactive)",
    }.get(mode, mode)

    return f"""
## TIME & STATE
  Now:  {now}
  Mode: {mode_label}{ctx_pct}"""


# ─── §16.3 + §18.10 Active Team + Family Bios ────────────────────────────────

def _active_team_block(active_agents: list, modules: dict = None) -> str:
    """Inject ACTIVE TEAM and family bios if enabled."""
    if not active_agents:
        return ""
    if modules and not modules.get("family_bios_in_context", True):
        return ""

    lines = ["\n## ACTIVE TEAM"]
    for a in active_agents:
        name    = a.get("name", a.get("id", "?"))
        model   = a.get("model", "?")
        role    = a.get("role", "main")
        bio     = a.get("bio", a.get("description", ""))
        ctx_pct = a.get("context_pct", "")
        ctx_str = f" ctx:{ctx_pct}%" if ctx_pct else ""
        bio_str = f" — {bio}" if bio else ""
        lines.append(f"  [{role}] {name} ({model}){ctx_str}{bio_str}")

    return "\n".join(lines)
