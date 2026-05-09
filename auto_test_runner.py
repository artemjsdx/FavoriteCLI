#!/usr/bin/env python3
"""FavoriteCLI Automated Test Runner"""
import sys, json, time, traceback
sys.path.insert(0, '/storage/emulated/0/Цхранилище/Project/FavoriteCLI')

results = []
PASS, FAIL = 'PASS', 'FAIL'

def test(name, fn):
    try:
        fn()
        results.append((PASS, name, ''))
        print(f'  [PASS] {name}')
    except Exception as e:
        results.append((FAIL, name, str(e)[:120]))
        print(f'  [FAIL] {name}: {str(e)[:100]}')

# БЛОК 1: СИНТАКСИС
print('\n=== БЛОК 1: СИНТАКСИС ===')
import ast, pathlib

def t_syntax():
    base = pathlib.Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/favorite')
    files = list(base.rglob('*.py'))
    bad = []
    for f in files:
        try:
            ast.parse(f.read_text('utf-8', errors='replace'))
        except SyntaxError as e:
            bad.append(f'{f.name}: {e}')
    assert not bad, f'SyntaxError: {bad[:3]}'
    print(f'    -> {len(files)} файлов ОК')
test('T01: Синтаксис всех .py', t_syntax)

# БЛОК 2: ИМПОРТЫ
print('\n=== БЛОК 2: ИМПОРТЫ ===')

def t_import_app():
    from favorite.app import _build_registry
    r = _build_registry()
    cnt = len(r._commands)
    assert cnt >= 40, f'Команд: {cnt}'
    print(f'    -> {cnt} команд')
test('T02: app._build_registry()', t_import_app)

def t_import_crew():
    from favorite.agent.crew import get_crew, Crew, MainAgent
    c = get_crew()
    assert isinstance(c, Crew)
test('T03: import crew', t_import_crew)

def t_import_crosschat():
    from favorite.agent.cross_chat import get_bus
    bus = get_bus()
    assert bus is not None
test('T04: import cross_chat', t_import_crosschat)

def t_import_reincarnation():
    from favorite.agent.reincarnation_keeper import full_reincarnation_protocol
    assert callable(full_reincarnation_protocol)
test('T05: import reincarnation_keeper', t_import_reincarnation)

def t_import_mcp():
    from favorite.mcp.manager import get_mcp_manager
    mgr = get_mcp_manager()
    assert mgr is not None
test('T06: import mcp.manager', t_import_mcp)

def t_import_tags():
    from favorite.agent.tags import extract_tags
    tags = extract_tags('<THINK>test</THINK><CMD>ls</CMD>')
    assert len(tags) >= 1, f'tags={tags}'
    print(f'    -> {len(tags)} тегов')
test('T07: tags.extract_tags()', t_import_tags)

def t_import_executor():
    from favorite.agent.executor import execute_tags
    assert callable(execute_tags)
test('T08: import executor', t_import_executor)

# БЛОК 3: CREW
print('\n=== БЛОК 3: CREW ===')

def t_crew_list():
    from favorite.agent.crew import get_crew
    c = get_crew()
    agents = c.list_all()
    print(f'    -> {len(agents)} агентов')
test('T09: crew.list_all()', t_crew_list)

def t_crew_leading():
    from favorite.agent.crew import get_crew
    c = get_crew()
    leading = c.leading()
    print(f'    -> leading={leading.name if leading else "нет"}')
test('T10: crew.leading()', t_crew_leading)

def t_crew_add_remove():
    from favorite.agent.crew import get_crew
    c = get_crew()
    a = c.add(name='test-tmp', provider='openrouter', model_id='x/y', api_key='key', role='test')
    assert c.get(a.id) is not None
    assert c.remove(a.id)
    assert c.get(a.id) is None
test('T11: crew.add() + remove()', t_crew_add_remove)

def t_family_summary():
    from favorite.agent.crew import get_crew
    s = get_crew().family_summary()
    assert isinstance(s, str)
    print(f'    -> summary len={len(s)}')
test('T12: crew.family_summary()', t_family_summary)

# БЛОК 4: CROSS CHAT
print('\n=== БЛОК 4: CROSS CHAT ===')

def t_bus_send():
    from favorite.agent.cross_chat import get_bus
    bus = get_bus()
    msg_id = bus.send('brief', 'alpha', 'beta', 'Test brief content S1')
    assert msg_id, 'msg_id пустой'
    msgs = bus.get_messages('beta', unread_only=True)
    found = any('Test brief content S1' in m.content for m in msgs)
    assert found, f'Не найдено в {len(msgs)} сообщениях'
test('T13: bus.send() + get_messages()', t_bus_send)

def t_bus_brief_family():
    from favorite.agent.cross_chat import get_bus
    bus = get_bus()
    ids = bus.brief_family('sender', 'Общий бриф')
    print(f'    -> {len(ids)} id-шников')
test('T14: bus.brief_family()', t_bus_brief_family)

# БЛОК 5: REINCARNATION
print('\n=== БЛОК 5: REINCARNATION ===')

def t_reincarnation():
    from favorite.agent.reincarnation_keeper import full_reincarnation_protocol
    result = full_reincarnation_protocol(
        session_id='test-auto-sess',
        dying_agent_name='main-1',
        brief='Context: FavoriteCLI tests. Topics: crew, MCP.',
        reset_callback=None
    )
    assert isinstance(result, dict), f'type={type(result)}'
    keys = list(result.keys())
    print(f'    -> result keys: {keys}')
test('T15: full_reincarnation_protocol()', t_reincarnation)

def t_reincarnation_file():
    p = pathlib.Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/sessions/test-auto-sess/reincarnation_notes.jsonl')
    assert p.exists(), f'Файл не найден: {p}'
    lines = [l for l in p.read_text().strip().split('\n') if l]
    print(f'    -> {len(lines)} записей')
test('T16: reincarnation_notes.jsonl создан', t_reincarnation_file)

# БЛОК 6: MCP
print('\n=== БЛОК 6: MCP ===')

def t_mcp_list():
    from favorite.mcp.manager import get_mcp_manager
    mgr = get_mcp_manager()
    servers = mgr.list_servers()
    assert isinstance(servers, list)
    print(f'    -> {len(servers)} серверов')
test('T17: mcp.list_servers()', t_mcp_list)

def t_mcp_all_tools():
    from favorite.mcp.manager import get_mcp_manager
    mgr = get_mcp_manager()
    tools = mgr.all_tools()
    assert isinstance(tools, dict)
    print(f'    -> all_tools keys={len(tools)}')
test('T18: mcp.all_tools()', t_mcp_all_tools)

# БЛОК 7: TAGS
print('\n=== БЛОК 7: TAGS ===')

def t_tag_think():
    from favorite.agent.tags import extract_tags
    tags = extract_tags('<THINK>think text</THINK>')
    assert any(t.name.upper() == 'THINK' for t in tags)
test('T19: tag THINK', t_tag_think)

def t_tag_mcp():
    from favorite.agent.tags import extract_tags
    tags = extract_tags('<MCP_CALL server="s" tool="t">{}</MCP_CALL>')
    names = [t.name.upper() for t in tags]
    assert any('MCP' in n for n in names), f'names={names}'
test('T20: tag MCP_CALL', t_tag_mcp)

def t_tag_reincarnate():
    from favorite.agent.tags import extract_tags
    tags = extract_tags('<REINCARNATE reason="ctx_full">brief</REINCARNATE>')
    names = [t.name.upper() for t in tags]
    assert any('REINCARNATE' in n for n in names), f'names={names}'
test('T21: tag REINCARNATE', t_tag_reincarnate)

# БЛОК 8: MODEL ROUTER
print('\n=== БЛОК 8: MODEL ROUTER ===')

def t_model_router():
    from favorite.agent.model_router import RouterModule
    print(f'    -> RouterModule OK')
test('T22: import model_router', t_model_router)

# ИТОГИ
print('\n' + '='*55)
passed = sum(1 for s,_,_ in results if s==PASS)
failed = sum(1 for s,_,_ in results if s==FAIL)
print(f'ИТОГ: {passed} PASS  /  {failed} FAIL  из {len(results)}')
if failed:
    print('\nПРОВАЛЕНЫ:')
    for s,n,e in results:
        if s==FAIL:
            print(f'  x {n}')
            print(f'    {e}')
print('='*55)
sys.exit(0 if failed == 0 else 1)
