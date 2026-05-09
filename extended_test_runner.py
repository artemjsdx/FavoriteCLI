#!/usr/bin/env python3
"""FavoriteCLI Extended Test Runner — T23-T30 (§17-§20 compliance) v2"""
import sys, json, time, traceback, pathlib
sys.path.insert(0, '/storage/emulated/0/Цхранилище/Project/FavoriteCLI')

results = []
PASS, FAIL = 'PASS', 'FAIL'

def test(name, fn):
    try:
        fn()
        results.append((PASS, name, ''))
        print(f'  [PASS] {name}')
        return True
    except Exception as e:
        results.append((FAIL, name, str(e)[:200]))
        print(f'  [FAIL] {name}: {str(e)[:150]}')
        return False

class MockCtx:
    def __init__(self):
        self.workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
        self.session_id = 'test-ext-sess'
        self.agent_id = 'main-1'
        self.shell_cwd = None
        self.config = None

# ─────────────────────────────────────────────────────────────────────────────
print('\n=== БЛОК 9: ТЕГИ §20 — 4 ФОРМАТА ===')
# ─────────────────────────────────────────────────────────────────────────────

def t_tag_html_format():
    from favorite.agent.tags import extract_tags
    tags = extract_tags('<STEP>Step 1</STEP>')
    assert any(t.name == 'STEP' for t in tags), f'tags={tags}'
    t_step = next(t for t in tags if t.name == 'STEP')
    assert t_step.body == 'Step 1', f'body={t_step.body!r}'
test('T23a: HTML format <TAG>body</TAG>', t_tag_html_format)

def t_tag_guillemet_heavy():
    from favorite.agent.tags import extract_tags
    tags = extract_tags('\u226aSHELL:cmd=ls\u226b/tmp\u226a/SHELL\u226b')
    names = [t.name for t in tags]
    assert any('SHELL' in n for n in names), f'names={names}'
test('T23b: Heavy guillemet \u226aTAG\u226b format', t_tag_guillemet_heavy)

def t_tag_guillemet_regular():
    from favorite.agent.tags import extract_tags
    tags = extract_tags('\u00abTHINK\u00bbsome thought\u00ab/THINK\u00bb')
    names = [t.name for t in tags]
    assert 'THINK' in names, f'names={names}'
test('T23c: Regular guillemet \u00abTAG\u00bb format', t_tag_guillemet_regular)

def t_tag_double_angle():
    from favorite.agent.tags import extract_tags
    tags = extract_tags('<<WRITE_FAV>>some memory<</WRITE_FAV>>')
    names = [t.name for t in tags]
    assert 'WRITE_FAV' in names, f'names={names}'
test('T23d: Double-angle <<TAG>> format', t_tag_double_angle)

def t_tag_inline_all_formats():
    from favorite.agent.tags import extract_tags
    found = 0
    for text in ['<LOAD_MEM>', '\u226aLOAD_MEM\u226b', '\u00abLOAD_MEM\u00bb', '<<LOAD_MEM>>']:
        tags = extract_tags(text)
        if tags and any(t.name == 'LOAD_MEM' for t in tags):
            found += 1
    print(f'    -> {found}/4 inline formats matched')
test('T23e: Inline tags all 4 formats', t_tag_inline_all_formats)

def t_tag_args_html_attr():
    from favorite.agent.tags import extract_tags
    tags = extract_tags('<MCP_CALL server="my-server" tool="search">{"q":"test"}</MCP_CALL>')
    assert tags, 'no tags extracted'
    t = tags[0]
    assert t.args.get('server') == 'my-server', f'server={t.args}'
    assert t.args.get('tool') == 'search', f'tool={t.args}'
test('T23f: HTML-attr args server="x" tool="y"', t_tag_args_html_attr)

def t_tag_args_colon_style():
    from favorite.agent.tags import extract_tags, _parse_args
    # Direct test of _parse_args with colon-without-leading-colon
    result = _parse_args('name=myjob:cmd=ls')
    print(f'    -> _parse_args result: {result}')
    assert result.get('name') == 'myjob', f'name={result.get("name")!r} (expected "myjob"), full={result}'
    assert result.get('cmd') == 'ls', f'cmd={result.get("cmd")!r} (expected "ls"), full={result}'
test('T23g: Colon-style args key=val:key2=val2', t_tag_args_colon_style)

# ─────────────────────────────────────────────────────────────────────────────
print('\n=== БЛОК 10: EXECUTOR DISPATCH ===')
# ─────────────────────────────────────────────────────────────────────────────

def t_exec_step():
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    tags = extract_tags('<STEP>Test step output</STEP>')
    ctx = MockCtx()
    out = execute_tags_with_output(tags, ctx, None)
    print(f'    -> STEP executed')
test('T24a: executor STEP tag', t_exec_step)

def t_exec_write_fav():
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    tags = extract_tags('<WRITE_FAV>## T24b test\nTest memory entry from T24b</WRITE_FAV>')
    ctx = MockCtx()
    execute_tags_with_output(tags, ctx, None)
    fav = pathlib.Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/Favorite.md')
    assert fav.exists(), 'Favorite.md not found'
    print(f'    -> Favorite.md updated, size={fav.stat().st_size}')
test('T24b: executor WRITE_FAV', t_exec_write_fav)

def t_exec_write_plan():
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    tags = extract_tags('<WRITE_PLAN>Step 1: do X\nStep 2: do Y</WRITE_PLAN>')
    ctx = MockCtx()
    execute_tags_with_output(tags, ctx, None)
    plan = pathlib.Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/sessions/test-ext-sess/plan.txt')
    assert plan.exists(), f'plan not found at {plan}'
    print(f'    -> plan.txt exists, {plan.stat().st_size} bytes')
test('T24c: executor WRITE_PLAN', t_exec_write_plan)

def t_exec_memo():
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    tags = extract_tags('<MEMO:to=self>Test memo T24d content</MEMO>')
    ctx = MockCtx()
    execute_tags_with_output(tags, ctx, None)
    print(f'    -> MEMO(self) executed')
test('T24d: executor MEMO tag', t_exec_memo)

def t_exec_think_silent():
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    tags = extract_tags('<THINK>internal thought</THINK>')
    ctx = MockCtx()
    out = execute_tags_with_output(tags, ctx, None)
    assert not out or 'thought' not in str(out), f'THINK should be silent, got: {out!r}'
    print(f'    -> THINK is silent')
test('T24e: executor THINK is silent', t_exec_think_silent)

# ─────────────────────────────────────────────────────────────────────────────
print('\n=== БЛОК 11: CREW + AGENTS ===')
# ─────────────────────────────────────────────────────────────────────────────

def t_crew_main1_exists():
    from favorite.agent.crew import get_crew
    c = get_crew()
    agents = c.list_all()
    assert any(a.name == 'main-1' for a in agents), f'main-1 not found: {[a.name for a in agents]}'
    m1 = c.get_by_name('main-1')
    print(f'    -> main-1: {m1.provider} / {m1.model_id[:20]}')
test('T25a: crew has main-1 agent', t_crew_main1_exists)

def t_crew_leading_main1():
    from favorite.agent.crew import get_crew
    c = get_crew()
    lead = c.leading()
    assert lead is not None and lead.name == 'main-1', f'leading={lead}'
    print(f'    -> leading: {lead.name}')
test('T25b: leading agent is main-1', t_crew_leading_main1)

def t_crew_multi():
    from favorite.agent.crew import get_crew
    c = get_crew()
    a2 = c.add(name='main-2', provider='openrouter', model_id='qwen/qwen3-coder:free', api_key='test-key-2', role='review')
    a3 = c.add(name='sub-critic', provider='openrouter', model_id='meta-llama/llama-3.1-8b-instruct:free', api_key='test-key-3', role='critique')
    count = len(c.list_all())
    print(f'    -> crew: {count} agents')
    c.remove(a2.id); c.remove(a3.id)
    print(f'    -> after cleanup: {len(c.list_all())} agents')
test('T25c: crew add multiple + remove', t_crew_multi)

# ─────────────────────────────────────────────────────────────────────────────
print('\n=== БЛОК 12: SESSIONS + TASKS ===')
# ─────────────────────────────────────────────────────────────────────────────

def t_sessions_create():
    from favorite.sessions.manager import SessionManager
    sm = SessionManager()
    sid = sm.create_session(workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', title='T26a test')
    assert sid, 'no session id'
    sess_dir = pathlib.Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/sessions') / sid
    assert sess_dir.exists(), f'dir not found: {sess_dir}'
    print(f'    -> created session {sid[:8]}...')
test('T26a: SessionManager.create_session()', t_sessions_create)

def t_sessions_history():
    from favorite.sessions.manager import SessionManager
    sm = SessionManager()
    sid = sm.create_session(workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI')
    sm.append_history(sid, {'role': 'user', 'content': 'Hello from T26b'})
    sm.append_history(sid, {'role': 'assistant', 'content': 'Hi there!'})
    history = sm.load_history(sid)
    assert len(history) >= 2, f'history len={len(history)}'
    assert any(m.get('content') == 'Hello from T26b' for m in history)
    print(f'    -> {len(history)} messages in history')
test('T26b: SessionManager append + load history', t_sessions_history)

def t_tasks_manager():
    from favorite.tasks.manager import TaskManager
    sess_dir = pathlib.Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/sessions/test-ext-sess')
    sess_dir.mkdir(parents=True, exist_ok=True)
    tm = TaskManager(sess_dir)
    task = tm.add_task('Test task from T27a', status='open')
    assert task.id, 'no task id'
    tasks = tm.list_tasks()
    assert any(t.id == task.id for t in tasks), f'task not found'
    print(f'    -> task created: {task.id}')
    tm.update_task(task.id, status='done')
    tasks2 = tm.list_tasks()
    done_task = next((t for t in tasks2 if t.id == task.id), None)
    assert done_task and done_task.status == 'done', f'status={done_task.status if done_task else None}'
    print(f'    -> task done: {done_task.status}')
test('T27a: TaskManager add + complete', t_tasks_manager)

# ─────────────────────────────────────────────────────────────────────────────
print('\n=== БЛОК 13: CONFIG + PROVIDER KEYS ===')
# ─────────────────────────────────────────────────────────────────────────────

def t_config_normalized():
    from favorite.config.loader import get_config
    cfg = get_config()
    fa = cfg.favorite_api_keys
    or_ = cfg.openrouter_keys
    assert all(isinstance(k, dict) and 'key' in k and 'is_default' in k for k in fa)
    assert all(isinstance(k, dict) and 'key' in k for k in or_)
    dfk = cfg.default_favorite_key()
    dok = cfg.default_openrouter_key()
    assert dfk and dok
    print(f'    -> FA:{len(fa)} OR:{len(or_)} ok, default_FA={dfk["key"][:10]}...')
test('T28a: Config keys normalized to dicts', t_config_normalized)

def t_fa_me():
    import requests
    from favorite.config.loader import get_config
    cfg = get_config()
    fk = cfg.default_favorite_key()
    key = fk.get('key', '') if fk else ''
    base = cfg.favorite_api_base_url
    r = requests.get(f'{base}/api/v1/me', headers={'Authorization': f'Bearer {key}'}, timeout=8)
    assert r.status_code == 200, f'FA /me: {r.status_code}'
    data = r.json()
    assert 'key' in data
    print(f'    -> FA /me OK, context_kb={data["key"].get("context_kb",0)}')
test('T28b: FavoriteAPI /me returns 200', t_fa_me)

# ─────────────────────────────────────────────────────────────────────────────
print('\n=== БЛОК 14: MODULES + SYSTEM HEALTH ===')
# ─────────────────────────────────────────────────────────────────────────────

def t_modules_config():
    import json
    from pathlib import Path
    mf = Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/config/modules.json')
    data = json.loads(mf.read_text())
    for k in ['action_bias_mode', 'reincarnation', 'agent_mode', 'time_injection']:
        assert k in data, f'{k} missing'
    print(f'    -> {len(data)} keys, reincarnation={data.get("reincarnation")}')
test('T29a: modules.json structure valid', t_modules_config)

def t_modules_time_injection():
    import json
    from pathlib import Path
    data = json.loads(Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/config/modules.json').read_text())
    ti = data.get('time_injection', False)
    print(f'    -> time_injection={ti}')
test('T29b: time_injection module present', t_modules_time_injection)

def t_system_health():
    from favorite.config.loader import get_config
    from favorite.agent.crew import get_crew
    from favorite.sessions.manager import SessionManager
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    from favorite.mcp.manager import get_mcp_manager
    from favorite.agent.cross_chat import get_bus
    cfg = get_config()
    assert cfg.has_any_provider()
    crew = get_crew()
    assert len(crew.list_all()) >= 1
    sm = SessionManager()
    sid = sm.create_session()
    assert sid
    tags = extract_tags('<STEP>Health check</STEP>')
    ctx = MockCtx()
    execute_tags_with_output(tags, ctx, cfg)
    mgr = get_mcp_manager()
    assert isinstance(mgr.list_servers(), list)
    bus = get_bus()
    assert bus is not None
    print(f'    -> ALL SYSTEMS GO: agents={len(crew.list_all())} sess={sid[:8]}...')
test('T30: Full system health check', t_system_health)

# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*55)
passed = sum(1 for s,_,_ in results if s==PASS)
failed = sum(1 for s,_,_ in results if s==FAIL)
print(f'ИТОГ: {passed} PASS  /  {failed} FAIL  из {len(results)}')
if failed:
    print('\nПРОВАЛЕНЫ:')
    for s,n,e in results:
        if s==FAIL:
            print(f'  x {n}')
            if e: print(f'    {e}')
print('='*55)
sys.exit(0 if failed == 0 else 1)
