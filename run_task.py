import sys, re, time, traceback, threading, subprocess, uuid
try:
    import requests
except ImportError:
    requests = None
from pathlib import Path
CLI = Path(__file__).parent
sys.path.insert(0, str(CLI))
from favorite.config.loader import reload_config
from favorite.agent.llm import call_llm
from favorite.agent.system_prompt import build_system_prompt
from favorite.commands.base import CommandContext
from favorite.sessions.manager import SessionManager
from favorite.platform import detect_platform
from favorite.agent.continuity_inspector import inspect as ci_inspect, should_interrupt as ci_should_interrupt

TASK_FILE  = sys.argv[1]
OUT_PREFIX = sys.argv[2]
WORKDIR    = str(CLI)
OUTPUT     = CLI / f"{OUT_PREFIX}.log"
TASK       = (CLI / TASK_FILE).read_text(encoding='utf-8')

WRITE_RE  = re.compile(r'<WRITE_FILE:path=([^>]+)>(.*?)</WRITE_FILE>', re.DOTALL)
STEP_RE   = re.compile(r'<STEP>(.*?)</STEP>', re.DOTALL)
CONT_RE   = re.compile(r'<CONTINUE>(.*?)</CONTINUE>', re.DOTALL)
SEARCH_RE      = re.compile(r'<SKILL:name=websearch>(.*?)</SKILL>', re.DOTALL)
FETCH_RE       = re.compile(r'<SKILL:name=fetch_url>(.*?)</SKILL>', re.DOTALL)
DEVICE_CTRL_RE = re.compile(r'<SKILL:name=device_ctrl>(.*?)</SKILL>', re.DOTALL)
CMD_RE    = re.compile(r'<CMD>(.*?)</CMD>', re.DOTALL)
BG_CMD_RE = re.compile(r'<CMD\s+bg=["\'\']?(\d+)["\'\']?>(.*?)</CMD>', re.DOTALL)
SUB_AGENT_RE = re.compile(r'<SUB_AGENT:role=([^>\n]+)>(.*?)</SUB_AGENT>', re.DOTALL)
CONFIRM_CMD_RE = re.compile(r'<CONFIRM_CMD>(.*?)</CONFIRM_CMD>', re.DOTALL)

AUTO_SYS = '''
=== AUTO MODE ===
Работай автономно. Ограничений по шагам НЕТ — работай до полного завершения задачи.

ИНСТРУМЕНТЫ:
  <CMD>команда</CMD>                              — shell-команда (60s timeout)
  <CONFIRM_CMD>опасная_команда</CONFIRM_CMD>      — опасная команда (явное подтверждение)
  <CMD bg="600">долгая команда</CMD>              — фоновый запуск, результат придёт как [BG RESULTS]
  <SKILL:name=websearch>запрос</SKILL>            — поиск в интернете
  <SKILL:name=fetch_url>https://...</SKILL>       — загрузить URL
  <SKILL:name=device_ctrl>ACTION[:arg=val]</SKILL> — управление Android-устройством (см. раздел DEVICE CONTROL)
  <WRITE_FILE:path=путь>содержимое</WRITE_FILE>  — записать файл

DEVICE CONTROL быстрая шпаргалка (подробнее в системном промпте выше):
  apps | launch:pkg=... | screenshot | screenshot:q=вопрос
  ui_dump | tap:x=N:y=N | tap_text:text=... | press:key=back
  swipe:x1=...:y1=...:x2=...:y2=... | wait:ms=N | device_info

ПЕТЛЯ-ДЕТЕКТОР (Overseer):
  Если одна и та же команда повторяется 3+ раз → предупреждение.
  При предупреждении: немедленно смени стратегию.

Сигнал продолжения: <CONTINUE>что дальше</CONTINUE>
Сигнал завершения: финальное резюме без CONTINUE.

  ПРИВЫЧКА ХОРОШЕГО РАЗРАБОТЧИКА:
    После каждого действия — убедись что оно сработало.
    Написал скрипт → запусти его. Запустил команду → посмотри вывод.
    Не переходи к следующему шагу пока не видел реальный вывод текущего.
=== END AUTO MODE ===
'''

cfg_ref: list = [None]  # module-level cfg for process_skills sub-agent dispatch
ctx_ref: list = [None]  # module-level ctx for process_skills device_ctrl dispatch

def log(msg):
    s = str(msg)
    print(s, flush=True)
    with open(OUTPUT, 'a', encoding='utf-8') as f: f.write(s + '\n')

# ── Background job system ─────────────────────────────────────────────────
_BG_JOBS: list[dict] = []
_BG_LOCK = threading.Lock()

def launch_bg_cmd(cmd_str: str, timeout_sec: int) -> str:
    job_id = uuid.uuid4().hex[:8]
    start  = time.time()
    proc   = subprocess.Popen(
        cmd_str, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, cwd=WORKDIR
    )
    with _BG_LOCK:
        _BG_JOBS.append({'id': job_id, 'cmd': cmd_str, 'proc': proc,
                         'start': start, 'timeout': timeout_sec})
    log(f'  [bg:{job_id}] запущен (max {timeout_sec}s): {cmd_str[:70]}')
    return f'[bg:{job_id}] ЗАПУЩЕНО в фоне (до {timeout_sec}s) — результат придёт автоматически'

def collect_bg_results() -> str:
    now, done, pending = time.time(), [], []
    with _BG_LOCK:
        for job in _BG_JOBS:
            elapsed = now - job['start']
            ret = job['proc'].poll()
            if ret is not None:
                out = (job['proc'].stdout.read() if job['proc'].stdout else '') or ''
                done.append((job, elapsed, out, False))
            elif elapsed >= job['timeout']:
                job['proc'].kill()
                out = (job['proc'].stdout.read() if job['proc'].stdout else '') or ''
                done.append((job, elapsed, out, True))
            else:
                pending.append(job)
        _BG_JOBS[:] = pending
    if not done:
        return ''
    parts = []
    for job, elapsed, out, timed_out in done:
        out = (out or '').strip()
        MAX = 8000
        if len(out) > MAX:
            out = out[:MAX] + f'\n...[{len(out)-MAX} chars truncated]'
        status = f'TIMEOUT {job["timeout"]}s' if timed_out else f'OK за {elapsed:.1f}s'
        parts.append(
            f'[bg:{job["id"]}] ЗАВЕРШЕНО ({status})\n'
            f'$ {job["cmd"]}\n{out or "(no output)"}'
        )
    return '\n\n'.join(parts)

# ── Loop detector (Overseer) ───────────────────────────────────────────────
_CMD_HISTORY: list[str] = []

def check_loop(resp: str) -> str | None:
    cmds  = [m.strip() for m in CMD_RE.findall(resp)]
    cmds += [m[1].strip() for m in BG_CMD_RE.findall(resp)]
    _CMD_HISTORY.extend(cmds)
    if len(_CMD_HISTORY) < 6:
        return None
    last6 = _CMD_HISTORY[-6:]
    for cmd in set(last6):
        if last6.count(cmd) >= 3:
            return (
                f'[OVERSEER] Команда повторяется {last6.count(cmd)}x подряд: `{cmd[:80]}`\n'
                f'Смени стратегию — этот путь не работает. Попробуй другой подход.'
            )
    return None

# ── Tool implementations ───────────────────────────────────────────────────

_DANGER_PATTERNS = [
    r'rm\s+-rf\s+/',              # rm -rf / (wipe root)
    r'rm\s+-rf\s+~',              # rm -rf ~ (wipe home)
    r'\|\s*bash',                 # pipe to bash (wget|bash, curl|bash)
    r'\|\s*sh\b',                # pipe to sh
    r'mkfs\.',                     # format filesystem
    r'dd\s+if=',                   # dd wipe
    r'chmod\s+777\s+/',           # chmod 777 root
    r':(\s*)\{.*\}\s*;\s*:',  # fork bomb :(){ :|:& };:
]
_DANGER_RE = re.compile('|'.join(_DANGER_PATTERNS), re.IGNORECASE)

def _is_dangerous(cmd_str: str) -> bool:
    return bool(_DANGER_RE.search(cmd_str))

def _danger_confirm_msg(cmd_str: str) -> str:
    return (
        f'[SAFETY CONFIRM] Команда совпадает с опасным паттерном: `{cmd_str[:100]}`\n'
        f'Ты точно хочешь её выполнить?\n'
        f'Если да — используй тег <CONFIRM_CMD> вместо <CMD>:\n'
        f'  <CONFIRM_CMD>{cmd_str}</CONFIRM_CMD>\n'
        f'Если это был пример/эксплойт в отчёте — используй markdown ```bash блок, не CMD тег.'
    )

def do_confirmed_cmd(cmd_str: str) -> str:
    """Выполняет команду БЕЗ проверки на опасность — агент явно подтвердил намерение."""
    log(f'  [CONFIRM_CMD] {cmd_str[:80]}')
    try:
        r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True,
                           timeout=120, cwd=WORKDIR)
        out = (r.stdout or '').strip()
        err = (r.stderr or '').strip()
        combined = '\n'.join(x for x in [out, err] if x)
        MAX = 8000
        if len(combined) > MAX:
            combined = combined[:MAX] + f'\n...[truncated {len(combined)-MAX} chars]'
        return combined or f'(exit {r.returncode}, no output)'
    except subprocess.TimeoutExpired:
        return 'ERROR: timeout (120s)'
    except Exception as e:
        return f'ERROR: {e}'

def do_cmd(cmd_str: str) -> str:
    if _is_dangerous(cmd_str):
        log(f'  [SAFETY ASK] {cmd_str[:80]}')
        return _danger_confirm_msg(cmd_str)
    try:
        r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True,
                           timeout=120, cwd=WORKDIR)
        out = (r.stdout or '').strip()
        err = (r.stderr or '').strip()
        combined = '\n'.join(x for x in [out, err] if x)
        MAX = 8000
        if len(combined) > MAX:
            combined = combined[:MAX] + f'\n...[truncated {len(combined)-MAX} chars]'
        return combined or f'(exit {r.returncode}, no output)'
    except subprocess.TimeoutExpired:
        return 'ERROR: timeout (120s)'
    except Exception as e:
        return f'ERROR: {e}'

def do_websearch(query: str) -> str:
    try:
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        r = requests.get('https://html.duckduckgo.com/html/', params={'q': query},
            headers={'User-Agent': ua}, timeout=10)
        snips  = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        titles = re.findall(r'<a class="result__a"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        out = []
        for i in range(min(4, len(snips))):
            t = re.sub(r'<[^>]+>', '', titles[i] if i < len(titles) else '').strip()
            s = re.sub(r'<[^>]+>', '', snips[i]).strip()
            out.append(f'[{i+1}] {t}\n{s}')
        return '\n\n'.join(out) or 'No results'
    except Exception as e: return f'search error: {e}'

def do_fetch(url: str) -> str:
    try:
        h = {'User-Agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36',
             'Accept': 'text/html,application/json,*/*'}
        r = requests.get(url.strip(), headers=h, timeout=15)
        return f'HTTP {r.status_code}\n{r.text[:5000]}'
    except Exception as e: return f'fetch error: {e}'

def process_skills(resp: str) -> str:
    parts = []
    for m in BG_CMD_RE.finditer(resp):
        bg_timeout = int(m.group(1))
        bg_cmd     = m.group(2).strip()
        result     = launch_bg_cmd(bg_cmd, bg_timeout)
        parts.append(result)
    for m in SUB_AGENT_RE.finditer(resp):
          role = m.group(1).strip()
          task = m.group(2).strip()
          log(f'  [sub-agent:{role}] dispatching...')
          try:
              from favorite.agent.sub_agent import run_sub_agent
              sa_result = run_sub_agent(role, task, cfg_ref[0] or reload_config())
              result_str = f'[sub-agent {role} output]:\n{sa_result}'
          except Exception as e:
              result_str = f'[sub-agent {role} ERROR]: {e}'
          log(f'  [sub-agent:{role}] done ({len(result_str)} chars)')
          parts.append(result_str)
    for m in CONFIRM_CMD_RE.finditer(resp):
        cmd_str = m.group(1).strip()
        log(f'  [confirm-cmd] {cmd_str[:80]}')
        result  = do_confirmed_cmd(cmd_str)
        parts.append('[CONFIRM_CMD: ' + cmd_str[:60] + ']\n' + result)
    for m in CMD_RE.finditer(resp):
        cmd_str = m.group(1).strip()
        log(f'  [cmd] {cmd_str[:80]}')
        result  = do_cmd(cmd_str)
        parts.append('[CMD: ' + cmd_str[:60] + ']\n' + result)
    for m in SEARCH_RE.finditer(resp):
        q = m.group(1).strip()
        log(f'  [search] {q[:60]}')
        parts.append(f'[websearch: {q}]\n{do_websearch(q)}')
    for m in FETCH_RE.finditer(resp):
        u = m.group(1).strip()
        log(f'  [fetch] {u[:60]}')
        parts.append(f'[fetch_url: {u}]\n{do_fetch(u)}')
    for m in DEVICE_CTRL_RE.finditer(resp):
        args_str = m.group(1).strip()
        log(f'  [device_ctrl] {args_str[:80]}')
        try:
            from favorite.skills.device_ctrl import DeviceCtrlSkill
            result = DeviceCtrlSkill().run(args_str, ctx=ctx_ref[0], cfg=None)
        except Exception as e:
            result = f'[device_ctrl ERROR] {e}'
        parts.append(f'[device_ctrl: {args_str[:60]}]\n{result}')
    return '\n\n---\n\n'.join(parts)

def write_files(resp: str) -> list[str]:
    written = []
    for m in WRITE_RE.finditer(resp):
        rel     = m.group(1).strip()
        content = m.group(2)
        fpath   = CLI / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding='utf-8')
        written.append(rel)
        log(f'  wrote: {rel} ({len(content)} chars)')
    return written


# ── Action-claim mismatch detector ───────────────────────────────────────
_ACTION_WORDS = [
    'создан', 'создала', 'создал', 'запущен', 'запустил', 'запустила',
    'отправлен', 'отправил', 'выполнен', 'выполнил', 'установлен',
    'written', 'created', 'launched', 'sent', 'done', 'complete',
    'готово', 'сделано', 'записан', 'запушен', 'скачан',
]

def check_unverified_claims(resp: str) -> str | None:
    """If agent claims to have done something but used no tools — nudge to verify."""
    # Fix А (Вариант 1): WRITE_FILE ERROR always triggers verify nudge
    if 'WRITE_FILE ERROR' in resp:
        return ('[VERIFY] WRITE_FILE ERROR — файл НЕ записан. '
                'Исправь формат тега: <WRITE_FILE:path=путь>содержимое</WRITE_FILE>, '
                'затем проверь: ls -la <path>')
    has_tools = bool(
        CMD_RE.search(resp) or BG_CMD_RE.search(resp) or
        WRITE_RE.search(resp) or SEARCH_RE.search(resp) or FETCH_RE.search(resp) or
        SUB_AGENT_RE.search(resp) or CONFIRM_CMD_RE.search(resp) or
        DEVICE_CTRL_RE.search(resp)
    )
    if has_tools:
        return None  # Agent actually did something, no issue
    resp_lower = resp.lower()
    found = [w for w in _ACTION_WORDS if w in resp_lower]
    if found:
        return (
            f'[VERIFY] Не вижу вывода команды для: {found[:3]}. '
            f'Покажи реальный результат.'
        )
    return None

# ── Main loop — NO turn limit ──────────────────────────────────────────────
def main():
    OUTPUT.write_text(
        f'=== START {time.strftime("%Y-%m-%d %H:%M:%S")} task={TASK_FILE} ===\n',
        encoding='utf-8'
    )
    cfg = reload_config()
    cfg_ref[0] = cfg  # expose cfg to process_skills
    log(f'provider: {cfg.has_any_provider()}')
    mgr = SessionManager()
    sid = mgr.create_session(workdir=WORKDIR)
    ctx = CommandContext(workdir=WORKDIR, session_id=sid,
        platform=detect_platform(), config=cfg, mgr=mgr, registry=None)
    ctx.auto_mode = True
    ctx_ref[0] = ctx  # expose ctx to process_skills for device_ctrl
    base = build_system_prompt(cfg, WORKDIR, session_id=sid)
    messages = [
        {'role': 'system', 'content': base + AUTO_SYS},
        {'role': 'user',   'content': TASK},
    ]
    all_files = []
    turn = 0
    prev_responses: list[str] = []
    consecutive_warnings = 0
    while True:
        turn += 1
        log(f'\n=== TURN {turn} [{time.strftime("%H:%M:%S")}] ===')

        # Inject any ready bg results BEFORE LLM call
        bg_pre = collect_bg_results()
        if bg_pre:
            messages.append({'role': 'user', 'content': '[BG RESULTS]\n' + bg_pre})
            log(f'  [bg-pre] {len(bg_pre)} chars injected')

        try:
            resp = call_llm(messages, cfg)
        except Exception as e:
            log(f'LLM ERR: {e}\n{traceback.format_exc()}'); break

        log(f'chars: {len(resp)}')
        (CLI / f'{OUT_PREFIX}_turn_{turn}.txt').write_text(resp, encoding='utf-8')
        for s in STEP_RE.findall(resp): log(f'  STEP: {s.strip()[:100]}')

        skill_res = process_skills(resp)
        written   = write_files(resp)
        all_files.extend(written)
        messages.append({'role': 'assistant', 'content': resp})

        # ── Continuity Inspector (§25) ─────────────────────────────────────
        ci_result = ci_inspect(resp, prev_responses)
        prev_responses.append(resp)
        if len(prev_responses) > 10:
            prev_responses.pop(0)
        if ci_result['status'] == 'stuck':
            consecutive_warnings += 1
            log(f'  [CI] STUCK: {ci_result["reason"]}')
        elif ci_result['status'] == 'warning':
            consecutive_warnings += 1
            log(f'  [CI] WARNING: {ci_result["reason"]}')
        else:
            consecutive_warnings = 0

        fb = []
        if written:   fb.append(f'Files written: {written}')
        if skill_res: fb.append(f'Tool results:\n{skill_res}')

        warn = check_loop(resp)
        if warn:
            fb.append(warn)
            log('  [overseer] loop warning injected')

        unverified = check_unverified_claims(resp)
        is_polling = bool(re.search(r'sleep\s+\d+', resp))
        if unverified and not skill_res and not written and not is_polling:
            fb.append(unverified)
            log(f'  [verify-nudge] {unverified[:80]}')

        # Skip CI interrupt if agent is intentionally waiting (sleep in response)
        if ci_should_interrupt(ci_result, consecutive_warnings) and not is_polling:
            fb.append(
                f'[CONTINUITY INSPECTOR] Агент застрял: {ci_result["reason"]}\n'
                f'Сбрось контекст, смени подход или используй другой инструмент.'
            )
            log(f'  [CI] interrupt signal injected (consecutive={consecutive_warnings})')

        bg_post = collect_bg_results()
        if bg_post:
            fb.append('[BG RESULTS]\n' + bg_post)
            log(f'  [bg-post] {len(bg_post)} chars injected')

        if fb:
            messages.append({'role': 'user', 'content': '[OK] ' + '\n\n'.join(fb)})

        conts    = CONT_RE.findall(resp)
        has_tool = bool(SEARCH_RE.search(resp) or FETCH_RE.search(resp) or
                        CMD_RE.search(resp)    or BG_CMD_RE.search(resp))
        has_bg   = bool(_BG_JOBS)

        if conts:
            log(f'  CONT: {conts[0].strip()[:80]}')
        elif has_tool or has_bg:
            log('  (tools active)')
        elif not written and turn >= 2:
            log('=== DONE ==='); break

    log(f'=== END {time.strftime("%H:%M:%S")} turns={turn} files={all_files} ===')

main()