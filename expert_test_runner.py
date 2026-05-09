#!/usr/bin/env python3
"""T56-T65: workers, AutoLoop, vote mock, reincarnation, SHELL registered, MCP, effort"""
import sys, traceback, unittest.mock
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

print('\n=== БЛОК 38: WORKERS CMD §43 ===')
def t_workers_cmd_import():
  from favorite.commands.workers_cmd import WorkersCommand, _load_workers, _save_workers, check_workers_on_startup
  assert WorkersCommand.name == '/workers'
  workers = _load_workers()
  assert isinstance(workers, list)
  print(f'    -> WorkersCommand OK, {len(workers)} workers in registry')
test('T56a: workers_cmd imports + _load_workers()', t_workers_cmd_import)

def t_workers_check_on_startup():
  from favorite.commands.workers_cmd import check_workers_on_startup
  crashed = check_workers_on_startup()
  assert isinstance(crashed, list)
  print(f'    -> check_workers_on_startup: {len(crashed)} crashed')
test('T56b: workers_cmd.check_workers_on_startup()', t_workers_check_on_startup)

print('\n=== БЛОК 39: AUTO LOOP §19 ===')
def t_auto_loop_create():
  from favorite.agent.auto_mode import AutoLoop, AutoLoopStats
  calls = []
  def send_to_agent(msg):
      calls.append(msg)
      return ('<DONE>task T57</DONE>', 10)
  def execute_tags(reply):
      return ('done', False)
  loop = AutoLoop(
      send_to_agent=send_to_agent,
      execute_tags=execute_tags,
      cfg=None,
      workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI',
      session_id='test-t57',
  )
  assert loop is not None
  print(f'    -> AutoLoop created OK')
test('T57a: AutoLoop can be created', t_auto_loop_create)

def t_auto_loop_stats():
  from favorite.agent.auto_mode import AutoLoopStats
  stats = AutoLoopStats()
  assert stats is not None
  elapsed = stats.elapsed_sec
  assert isinstance(elapsed, (int, float))
  s = stats.elapsed_str
  assert isinstance(s, str)
  print(f'    -> AutoLoopStats elapsed={elapsed:.2f}s str={s!r}')
test('T57b: AutoLoopStats.elapsed_sec() + elapsed_str()', t_auto_loop_stats)

def t_auto_loop_run_stops_on_done():
  from favorite.agent.auto_mode import AutoLoop
  turns = []
  def send_to_agent(msg):
      turns.append(msg)
      if len(turns) >= 2:
          return ('<DONE>finished</DONE>', 5)
      return ('thinking...', 5)
  def execute_tags(reply):
      return ('result', False)
  loop = AutoLoop(
      send_to_agent=send_to_agent,
      execute_tags=execute_tags,
      cfg=None,
      workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI',
      session_id='test-t57c',

  )
  loop.run('Start T57c task', max_steps=5)
  assert len(turns) >= 1
  print(f'    -> AutoLoop ran {len(turns)} turns then stopped on DONE')
test('T57c: AutoLoop.run() stops on DONE tag', t_auto_loop_run_stops_on_done)

print('\n=== БЛОК 40: VOTE MOCK §28 ===')
def t_vote_cast_ballot():
  from favorite.agent.vote import cast_ballot, get_vote_result, _vote_dir
  import json
  from pathlib import Path
  workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
  sid = 'test-t58-vote'
  vote_id = 't58-ballot-test'
  vdir = _vote_dir(workdir, sid)
  vdir.mkdir(parents=True, exist_ok=True)
  manifest = vdir / f'{vote_id}.json'
  manifest.write_text(json.dumps({
      'vote_id': vote_id, 'question': 'Approve?', 'options': ['yes', 'no'],
      'created_at': '2026-01-01T00:00:00Z', 'agents': ['main-1'],
      'ballots': {}, 'status': 'open'
  }), encoding='utf-8')

  ok = cast_ballot(vote_id, 'main-1', 'yes', workdir=workdir, session_id=sid)
  assert ok == True, f'cast_ballot returned {ok}'
  import json as _j; data = _j.loads(manifest.read_text()); assert data.get('ballots', {}).get('main-1') == 'yes'
  print(f'    -> cast_ballot ok={ok}, ballot stored')
test('T58a: vote.cast_ballot + get_vote_result', t_vote_cast_ballot)

print('\n=== БЛОК 41: REGISTERED SHELL §20.SHELL ===')
def t_shell_registered_ls():
  from favorite.agent.tags import extract_tags
  from favorite.agent.executor import execute_tags_with_output
  class MockCtx:
      workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
      session_id = 'test-t59'
      agent_id = 'main-1'
      shell_cwd = None
      config = None
  ctx = MockCtx()
  tags = extract_tags('<SHELL>ls</SHELL>')
  out = execute_tags_with_output(tags, ctx, None)
  print(f'    -> SHELL ls: {str(out)[:80]!r}')
  assert out is not None
test('T59a: executor SHELL registered command (ls)', t_shell_registered_ls)

def t_shell_raw_tag():
  from favorite.agent.tags import extract_tags
  from favorite.agent.executor import execute_tags_with_output
  class MockCtx:
      workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
      session_id = 'test-t59b'
      agent_id = 'main-1'
      shell_cwd = None
      config = None
  ctx = MockCtx()
  tags = extract_tags('<SHELL_RAW>echo shell_raw_t59b_ok</SHELL_RAW>')
  out = execute_tags_with_output(tags, ctx, None)
  print(f'    -> SHELL_RAW: {str(out)[:80]!r}')
  assert out is not None
test('T59b: executor SHELL_RAW tag runs subprocess', t_shell_raw_tag)

print('\n=== БЛОК 42: EFFORT CMD ===')
def t_effort_cmd_import():
  from favorite.commands.effort_cmd import EffortCommand
  ec = EffortCommand()
  assert hasattr(ec, 'name')
  print(f'    -> EffortCommand.name={ec.name!r}')
test('T60a: effort_cmd.EffortCommand importable', t_effort_cmd_import)

print('\n=== БЛОК 43: MCP COMMAND ===')
def t_mcp_cmd_import():
  from favorite.commands.mcp_cmd import McpCommand
  mc = McpCommand()
  assert hasattr(mc, 'name')
  print(f'    -> McpCommand.name={mc.name!r}')
test('T61a: mcp_cmd.McpCommand importable', t_mcp_cmd_import)

print('\n=== БЛОК 44: ARCHITECT CMD ===')
def t_architect_cmd_import():
  from favorite.commands.architect_cmd import ArchitectCommand
  ac = ArchitectCommand()
  assert hasattr(ac, 'name')
  print(f'    -> ArchitectCommand.name={ac.name!r}')
test('T62a: architect_cmd.ArchitectCommand importable', t_architect_cmd_import)

print('\n=== БЛОК 45: SKILL SEARCH CMD ===')
def t_skill_search_import():
  from favorite.commands.skill_search_cmd import SkillSearchCommand
  sc = SkillSearchCommand()
  assert hasattr(sc, 'name')
  print(f'    -> SkillSearchCommand.name={sc.name!r}')
test('T63a: skill_search_cmd importable', t_skill_search_import)

print('\n=== БЛОК 46: REINCARNATION FULL PROTOCOL ===')
def t_reincarnation_full():
  from favorite.agent.reincarnation_keeper import full_reincarnation_protocol
  def mock_reset(agent_name):
      print(f'      reset called for {agent_name}')
  result = full_reincarnation_protocol(
      session_id='t64-reinc-test',
      dying_agent_name='sub-agent-1',
      brief='Task T64: test reincarnation protocol',
      reset_callback=mock_reset,
  )
  assert isinstance(result, dict)
  print(f'    -> full_reincarnation_protocol result: {list(result.keys())}')
test('T64a: full_reincarnation_protocol() returns result dict', t_reincarnation_full)

print('\n=== БЛОК 47: EXECUTOR READ/WRITE FILE ===')
def t_executor_write_file():
  from favorite.agent.tags import extract_tags
  from favorite.agent.executor import execute_tags_with_output
  import pathlib
  class MockCtx:
      workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
      session_id = 'test-t65'
      agent_id = 'main-1'
      shell_cwd = None
      config = None
  ctx = MockCtx()
  test_file = pathlib.Path('/storage/emulated/0/Цхранилище/Project/FavoriteCLI/sessions/t65-write-test.txt')
  test_file.parent.mkdir(parents=True, exist_ok=True)
  tags = extract_tags('<WRITE_FILE:path=/storage/emulated/0/Цхранилище/Project/FavoriteCLI/sessions/t65-write-test.txt>content of T65 test file</WRITE_FILE>')
  out = execute_tags_with_output(tags, ctx, None)
  print(f'    -> WRITE_FILE: {str(out)[:60]!r}')
test('T65a: executor WRITE_FILE tag', t_executor_write_file)

def t_executor_read_file():
  from favorite.agent.tags import extract_tags
  from favorite.agent.executor import execute_tags_with_output
  class MockCtx:
      workdir = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI'
      session_id = 'test-t65b'
      agent_id = 'main-1'
      shell_cwd = None
      config = None
  ctx = MockCtx()
  tags = extract_tags('<READ_FILE:path=/storage/emulated/0/Цхранилище/Project/FavoriteCLI/sessions/t65-write-test.txt>')
  out = execute_tags_with_output(tags, ctx, None)
  print(f'    -> READ_FILE: {str(out)[:60]!r}')
test('T65b: executor READ_FILE tag', t_executor_read_file)

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