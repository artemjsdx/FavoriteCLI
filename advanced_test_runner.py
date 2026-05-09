#!/usr/bin/env python3
"""T51-T55: continuity_inspector, cross_chat, reincarnation, compaction, steps"""
import sys, traceback
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

print('\n=== БЛОК 33: CONTINUITY INSPECTOR §25 ===')
def t_continuity_inspect_ok():
  from favorite.agent.continuity_inspector import inspect, should_interrupt
  result = inspect('Я выполнил задачу, вот результат.', [])
  assert isinstance(result, dict)
  print(f'    -> inspect OK: {list(result.keys())}')
test('T51a: continuity_inspector.inspect() returns dict', t_continuity_inspect_ok)
def t_continuity_loop_detection():
  from favorite.agent.continuity_inspector import inspect, should_interrupt
  looped_response = 'как я уже говорил, к сожалению я не могу это сделать'
  prev = [looped_response] * 3
  result = inspect(looped_response, prev)
  assert isinstance(result, dict)
  intr = should_interrupt(result, consecutive_warnings=3)
  assert isinstance(intr, bool)
  print(f'    -> loop detected? interrupt={intr}, result={result}')
test('T51b: continuity_inspector loop detection', t_continuity_loop_detection)

print('\n=== БЛОК 34: CROSS CHAT BUS ===')
def t_cross_chat_bus():
  from favorite.agent.cross_chat import CrossChatBus
  bus = CrossChatBus()
  msg_id = bus.send('info', 'test_agent', 'main-1', 'hello T52', ttl=60)
  assert msg_id is not None
  msgs = bus.get_messages('main-1')
  assert isinstance(msgs, list) and len(msgs) >= 1
  print(f'    -> send+recv OK: id={msg_id}, {len(msgs)} msgs')
test('T52a: CrossChatBus.send + get_messages', t_cross_chat_bus)
def t_cross_chat_brief():
  from favorite.agent.cross_chat import CrossChatBus
  bus = CrossChatBus()
  sent = bus.brief_family('main-1', 'Task complete: T52b test')
  assert isinstance(sent, list)
  print(f'    -> brief_family: sent to {len(sent)} agents')
test('T52b: CrossChatBus.brief_family()', t_cross_chat_brief)
def t_cross_chat_cleanup():
  from favorite.agent.cross_chat import CrossChatBus
  bus = CrossChatBus()
  n = bus.cleanup_expired()
  assert isinstance(n, int)
  print(f'    -> cleanup_expired: {n} removed')
test('T52c: CrossChatBus.cleanup_expired()', t_cross_chat_cleanup)

print('\n=== БЛОК 35: REINCARNATION KEEPER ===')
def t_reincarnation_keeper():
  from favorite.agent.reincarnation_keeper import full_reincarnation_protocol
  assert callable(full_reincarnation_protocol)
  print(f'    -> full_reincarnation_protocol importable')
test('T53a: reincarnation_keeper.full_reincarnation_protocol importable', t_reincarnation_keeper)
def t_reincarnation_select_keeper():
  from favorite.agent.reincarnation_keeper import select_keeper
  result = select_keeper('main-1', ['python', 'code', 'test'])
  print(f'    -> select_keeper result: {result}')
test('T53b: reincarnation_keeper.select_keeper()', t_reincarnation_select_keeper)
def t_reincarnation_log_history():
  from favorite.agent.reincarnation_keeper import log_to_history
  import pathlib
  log_to_history('t53c-session', {'event': 'test', 'agent': 'main-1'})
  hist_file = pathlib.Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/sessions/t53c-session/reincarnation_history.json')
  print(f'    -> log_to_history OK (file exists: {hist_file.exists()})')
test('T53c: reincarnation_keeper.log_to_history()', t_reincarnation_log_history)

print('\n=== БЛОК 36: COMPACTION ===')
def t_compaction_should_compact():
  from favorite.agent.compaction import should_compact
  short = [{'role': 'user', 'content': 'hi'}] * 5
  assert not should_compact(short)
  long_msgs = [{'role': 'user', 'content': 'x' * 200}] * 65
  assert should_compact(long_msgs)
  print(f'    -> should_compact: short=False, long=True OK')
test('T54a: compaction.should_compact()', t_compaction_should_compact)
def t_compaction_compact_messages():
  from favorite.agent.compaction import compact_messages
  import unittest.mock
  msgs = [{'role': 'user', 'content': 'a ' * 100}] * 70
  with unittest.mock.patch('favorite.agent.compaction._summarize', return_value='SUMMARY'):
      result = compact_messages(msgs, 't54b-sid', '/storage/emulated/0/Цхранилище/Project/FavoriteCLI')
  assert isinstance(result, list)
  assert len(result) < len(msgs)
  print(f'    -> compact {len(msgs)} → {len(result)} messages')
test('T54b: compaction.compact_messages() reduces history', t_compaction_compact_messages)

print('\n=== БЛОК 37: SUB AGENT ===')
def t_sub_agent_import():
  from favorite.agent.sub_agent import run_sub_agent, _is_sandbox_on
  assert callable(run_sub_agent)
  from favorite.config.loader import get_config
  cfg = get_config()
  sandbox_on = _is_sandbox_on(cfg)
  assert isinstance(sandbox_on, bool)
  print(f'    -> run_sub_agent importable, sandbox={sandbox_on}')
test('T55a: sub_agent.run_sub_agent importable', t_sub_agent_import)
def t_sub_roles_library():
  import json, pathlib
  p = pathlib.Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/favorite/agent/sub_roles_library.json')
  assert p.exists()
  roles = json.loads(p.read_text())
  assert isinstance(roles, list) and len(roles) > 0
  ids = [r['id'] for r in roles]
  print(f'    -> sub_roles: {len(roles)} roles: {ids[:5]}')
test('T55b: sub_roles_library.json has roles', t_sub_roles_library)

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
import sys as _sys
_sys.exit(0 if failed == 0 else 1)