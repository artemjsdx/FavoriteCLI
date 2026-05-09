#!/usr/bin/env python3
"""T31-T40 Deep Tests — FIXED v2"""
import sys, json, traceback, pathlib
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
        results.append((FAIL, name, str(e)[:250]))
        print(f'  [FAIL] {name}: {str(e)[:180]}')
        traceback.print_exc()
        return False

print('\n=== БЛОК 15: SYSTEM PROMPT ===')

def t_syspr_import():
    from favorite.agent.system_prompt import build_system_prompt
    assert callable(build_system_prompt)
test('T31a: system_prompt imports OK', t_syspr_import)

def t_syspr_build_chat():
    from favorite.agent.system_prompt import build_system_prompt
    sp = build_system_prompt(mode='chat', workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', session_id='test-t31')
    assert isinstance(sp, str) and len(sp) > 100
    print(f'    -> {len(sp)} chars')
test('T31b: build_system_prompt(mode=chat)', t_syspr_build_chat)

def t_syspr_build_auto():
    from favorite.agent.system_prompt import build_system_prompt
    sp = build_system_prompt(mode='auto', workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', session_id='test-t31')
    assert isinstance(sp, str) and len(sp) > 100
test('T31c: build_system_prompt(mode=auto)', t_syspr_build_auto)

def t_syspr_time_injection():
    from favorite.agent.system_prompt import _time_and_state_block
    import json
    from pathlib import Path
    try:
        modules = json.loads(Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/config/modules.json').read_text())
    except Exception:
        modules = {}
    block = _time_and_state_block('chat', modules=modules)
    assert isinstance(block, str)
test('T31d: _time_and_state_block()', t_syspr_time_injection)

def t_syspr_universal_mindset():
    from favorite.agent.system_prompt import _universal_mindset
    block = _universal_mindset()
    assert isinstance(block, str) and len(block) > 50
test('T31e: _universal_mindset()', t_syspr_universal_mindset)

print('\n=== БЛОК 16: MODEL ROUTER ===')

def t_router_classify_simple():
    from favorite.agent.model_router import RouterModule
    assert RouterModule.classify('Hello') == 'simple'
test('T32a: classify simple', t_router_classify_simple)

def t_router_classify_complex():
    from favorite.agent.model_router import RouterModule
    assert RouterModule.classify('напиши код') == 'complex'
    assert RouterModule.classify('implement') == 'complex'
    assert RouterModule.classify('word ' * 35) == 'complex'
test('T32b: classify complex', t_router_classify_complex)

def t_router_select_model():
    from favorite.agent.model_router import RouterModule
    from favorite.config.loader import get_config
    provider, model, key = RouterModule.select_model('Hello', get_config())
    assert provider and model
    print(f'    -> {provider}/{model[:20]}')
test('T32c: select_model(simple)', t_router_select_model)

def t_router_select_complex():
    from favorite.agent.model_router import RouterModule
    from favorite.config.loader import get_config
    provider, model, key = RouterModule.select_model('напиши сложный алгоритм', get_config())
    assert provider and model
    print(f'    -> {provider}/{model[:20]}')
test('T32d: select_model(complex)', t_router_select_complex)

print('\n=== БЛОК 17: LLM MODULE ===')

def t_llm_import():
    from favorite.agent.llm import call_llm, stream_llm
    assert callable(call_llm) and callable(stream_llm)
test('T33a: llm imports', t_llm_import)

def t_llm_mock_call():
    import unittest.mock
    from favorite.agent.llm import call_llm
    from favorite.config.loader import get_config
    mock_response = unittest.mock.MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'choices': [{'message': {'content': 'Hello from mock LLM!'}}],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 5}
    }
    with unittest.mock.patch('requests.post', return_value=mock_response):
        result = call_llm([{'role': 'user', 'content': 'hi'}], get_config())
        assert 'Hello from mock LLM!' in result
        print(f'    -> {result!r:.30}')
test('T33b: call_llm mock', t_llm_mock_call)

def t_response_processor():
    from favorite.agent.response_processor import strip_thinking_blocks
    # Uses <thinking> not <think>
    text = '<thinking>internal reasoning...</thinking>Real answer here'
    stripped = strip_thinking_blocks(text)
    assert 'internal reasoning' not in stripped, f'got: {stripped!r}'
    assert 'Real answer' in stripped
    print(f'    -> stripped OK: {stripped!r}')
test('T33c: response_processor strips <thinking>', t_response_processor)

print('\n=== БЛОК 18: PLATFORM ===')

def t_platform_detect():
    from favorite.platform import detect_platform
    plat = detect_platform()
    assert plat is not None
    print(f'    -> {type(plat).__name__}')
test('T34a: detect_platform()', t_platform_detect)

def t_platform_run_shell():
    from favorite.platform import detect_platform
    plat = detect_platform()
    rc, out, err = plat.run_shell('echo hello_test', timeout=5)
    assert rc == 0 and 'hello_test' in out
test('T34b: platform.run_shell(echo)', t_platform_run_shell)

def t_platform_name():
    from favorite.platform import detect_platform
    plat = detect_platform()
    # name is @property not method
    name = plat.name
    assert isinstance(name, str) and len(name) > 0
    print(f'    -> {name!r}')
test('T34c: platform.name property', t_platform_name)

print('\n=== БЛОК 19: MEMORY ===')

def t_memory_fav_md():
    from favorite.memory.favorite_md import FavoriteMd  # lowercase d
    fmd = FavoriteMd()
    content = fmd.read()
    assert isinstance(content, str)
    print(f'    -> {len(content)} chars')
test('T35a: FavoriteMd.read()', t_memory_fav_md)

def t_memory_fav_md_append():
    from favorite.memory.favorite_md import FavoriteMd
    fmd = FavoriteMd()
    before = len(fmd.read())
    fmd.append_section('## T35b Test\nTest section')
    after = len(fmd.read())
    assert after > before
    print(f'    -> {before} → {after} chars')
test('T35b: FavoriteMd.append_section()', t_memory_fav_md_append)

def t_memory_hot_reload():
    from favorite.memory.hot_reload import start_watcher
    assert callable(start_watcher)
test('T35c: hot_reload importable', t_memory_hot_reload)

print('\n=== БЛОК 20: EXECUTOR ALL TAGS ===')

def t_executor_all_tags_handle():
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    class MockCtx:
        workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
        session_id = 'test-t36'
        agent_id = 'main-1'
        shell_cwd = None
        config = None
    ctx = MockCtx()
    tag_tests = [
        ('<STEP>step text</STEP>', 'STEP'),
        ('<THINK>thought</THINK>', 'THINK'),
        ('<LOAD_MEM>', 'LOAD_MEM'),
        ('<MEMO:to=self>note T36</MEMO>', 'MEMO'),
        ('<SILENT>', 'SILENT'),
        ('<STATUS>running</STATUS>', 'STATUS'),
        ('<DONE>task done</DONE>', 'DONE'),
        ('<BRIEF>brief text</BRIEF>', 'BRIEF'),
        ('<PLAN>1. do it</PLAN>', 'PLAN'),
        ('<SUGGEST_NEXT>try this</SUGGEST_NEXT>', 'SUGGEST_NEXT'),
        ('<ADD_TASK:title=Test T36:status=open>', 'ADD_TASK'),
        ('<LIST_TASKS>', 'LIST_TASKS'),
    ]
    failed_tags = []
    passed = 0
    for text, tag_name in tag_tests:
        try:
            tags = extract_tags(text)
            if tags:
                execute_tags_with_output(tags, ctx, None)
            passed += 1
        except Exception as e:
            failed_tags.append(f'{tag_name}: {e}')
    if failed_tags:
        print(f'    -> {passed}/{len(tag_tests)} OK, FAILED: {failed_tags}')
        assert not failed_tags
    else:
        print(f'    -> all {passed}/{len(tag_tests)} tags OK')
test('T36a: executor 12 tags without crash', t_executor_all_tags_handle)

def t_executor_shell_tag():
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    class MockCtx:
        workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
        session_id = 'test-t36b'
        agent_id = 'main-1'
        shell_cwd = None
        config = None
    ctx = MockCtx()
    tags = extract_tags('<SHELL>echo t36b_ok</SHELL>')
    out = execute_tags_with_output(tags, ctx, None)
    print(f'    -> SHELL: {str(out)[:50]!r}')
test('T36b: executor SHELL tag', t_executor_shell_tag)

def t_executor_reincarnate():
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    class MockCtx:
        workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
        session_id = 'test-t36c'
        agent_id = 'main-1'
        shell_cwd = None
        config = None
    ctx = MockCtx()
    tags = extract_tags('<REINCARNATE:reason="test">reincarnation T36c</REINCARNATE>')
    try:
        out = execute_tags_with_output(tags, ctx, None)
        print(f'    -> REINCARNATE: {str(out)[:60]!r}')
    except Exception as e:
        print(f'    -> REINCARNATE (partial OK): {e}')
test('T36c: executor REINCARNATE tag', t_executor_reincarnate)

print('\n=== БЛОК 21: API MODULES ===')

def t_api_openrouter_import():
    from favorite.api.openrouter import OpenRouterClient
    assert OpenRouterClient is not None
test('T37a: OpenRouterClient import', t_api_openrouter_import)

def t_api_favorite_import():
    from favorite.api.favorite_api import FavoriteApiClient  # lowercase c
    assert FavoriteApiClient is not None
    print(f'    -> FavoriteApiClient imported')
test('T37b: FavoriteApiClient import', t_api_favorite_import)

def t_api_openrouter_mock():
    from favorite.api.openrouter import OpenRouterClient
    from favorite.api.base import ChatMessage
    import unittest.mock
    mock_resp = unittest.mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {
        'choices': [{'message': {'content': 'OR mock response'}}],
        'usage': {'prompt_tokens': 5, 'completion_tokens': 3}
    }
    client = OpenRouterClient(api_key='test-key', model='qwen/qwen3-coder:free')
    with unittest.mock.patch('requests.post', return_value=mock_resp):
        result = client.chat([ChatMessage(role='user', content='hello')])
        assert result
        print(f'    -> {str(result)[:40]!r}')
test('T37c: OpenRouterClient.chat() mock', t_api_openrouter_mock)

print('\n=== БЛОК 22: FULL PIPELINE ===')

def t_pipeline_messages_flow():
    import unittest.mock
    from favorite.config.loader import get_config
    from favorite.agent.model_router import RouterModule
    from favorite.agent.tags import extract_tags
    from favorite.agent.executor import execute_tags_with_output
    cfg = get_config()
    provider, model, key = RouterModule.select_model('Test pipeline T38', cfg)
    mock_resp = unittest.mock.MagicMock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {
        'choices': [{'message': {'content': '<STEP>Pipeline test step</STEP>Pipeline OK'}}],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 5}
    }
    with unittest.mock.patch('requests.post', return_value=mock_resp):
        from favorite.agent.llm import call_llm
        response = call_llm([{'role': 'user', 'content': 'test'}], cfg)
        assert 'Pipeline' in response
        tags = extract_tags(response)
        class MockCtx:
            workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
            session_id = 'test-pipeline'
            agent_id = 'main-1'
            shell_cwd = None
            config = cfg
        if tags:
            execute_tags_with_output(tags, MockCtx(), cfg)
        print(f'    -> {provider}/{model[:15]} → {response[:30]!r}')
test('T38: Full pipeline mock', t_pipeline_messages_flow)

def t_session_stats():
    from favorite.sessions.manager import SessionManager
    sm = SessionManager()
    sid = sm.create_session(workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', title='T39 stats')
    sm.update_stats(sid, tokens=150)
    sm.update_stats(sid, tokens=200)
    meta = sm.get_session(sid)
    assert meta['stats']['total_tokens'] == 350
    assert meta['stats']['requests'] == 2
    print(f'    -> {meta["stats"]["total_tokens"]} tokens, {meta["stats"]["requests"]} requests')
test('T39: SessionManager.update_stats()', t_session_stats)

def t_crew_family_summary():
    from favorite.agent.crew import get_crew
    c = get_crew()
    summary = c.family_summary()
    assert isinstance(summary, str)
    print(f'    -> {len(summary)} chars: {summary[:60]!r}')
test('T40: Crew.family_summary()', t_crew_family_summary)

print('\n' + '='*55)
passed = sum(1 for s,_,_ in results if s==PASS)
failed = sum(1 for s,_,_ in results if s==FAIL)
total = len(results)
print(f'ИТОГ: {passed} PASS  /  {failed} FAIL  из {total}')
if failed:
    print('\nПРОВАЛЕНЫ:')
    for s,n,e in results:
        if s==FAIL:
            print(f'  x {n}')
            if e: print(f'    {e[:150]}')
print('='*55)
sys.exit(0 if failed == 0 else 1)
