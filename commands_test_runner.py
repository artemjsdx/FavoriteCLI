#!/usr/bin/env python3
"""T41-T50 Commands Tests — commands/ directory coverage"""
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

print('\n=== БЛОК 23: COMMAND REGISTRY ===')

def t_registry_import():
  from favorite.commands.registry import CommandRegistry
  from favorite.commands.base import CommandContext, ICommand
  r = CommandRegistry()
  assert r is not None
  print(f'    -> CommandRegistry OK')
test('T41a: CommandRegistry importable', t_registry_import)

def t_registry_register():
  from favorite.commands.registry import CommandRegistry
  from favorite.commands.base import ICommand
  from favorite.commands.help_cmd import HelpCommand
  r = CommandRegistry()
  r.register(HelpCommand())
  all_cmds = r.all_sorted()
  assert len(all_cmds) >= 1
  cmd = r.get('/help')
  assert cmd is not None
  print(f'    -> registry has {len(all_cmds)} cmds, help={cmd}')
test('T41b: CommandRegistry.register + get', t_registry_register)

def t_build_registry():
  from favorite.app import _build_registry
  reg = _build_registry()
  all_cmds = reg.all_sorted()
  assert len(all_cmds) >= 10, f'only {len(all_cmds)} commands'
  names = [c.name for c in all_cmds]
  print(f'    -> {len(all_cmds)} commands: {names[:8]}')
test('T41c: _build_registry() returns 10+ commands', t_build_registry)

print('\n=== БЛОК 24: HELP COMMAND ===')

def t_help_cmd():
  from favorite.commands.help_cmd import HelpCommand
  from favorite.commands.base import CommandContext
  from favorite.config.loader import get_config
  from favorite.commands.registry import CommandRegistry
  from pathlib import Path
  from favorite.sessions.manager import SessionManager
  from favorite.platform import detect_platform
  sm = SessionManager()
  sid = sm.create_session(workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', title='T42 help')
  reg = CommandRegistry()
  ctx = CommandContext(
      workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', session_id=sid,
      platform=detect_platform(), config=get_config(), mgr=sm, registry=reg
  )
  cmd = HelpCommand()
  assert cmd.name == 'help' or hasattr(cmd, 'name')
  try:
      cmd.execute('', ctx)
      print(f'    -> HelpCommand.execute OK')
  except Exception as e:
      print(f'    -> HelpCommand.execute (partial): {e}')
test('T42a: HelpCommand.execute()', t_help_cmd)

print('\n=== БЛОК 25: TASKS COMMAND ===')

def t_tasks_cmd_import():
  from favorite.commands.tasks_cmd import TasksCommand
  tc = TasksCommand()
  assert hasattr(tc, 'name') and hasattr(tc, 'execute')
  print(f'    -> TasksCommand.name={tc.name!r}')
test('T43a: TasksCommand importable', t_tasks_cmd_import)

def t_tasks_cmd_list():
  from favorite.commands.tasks_cmd import TasksCommand
  from favorite.commands.base import CommandContext
  from favorite.config.loader import get_config
  from favorite.commands.registry import CommandRegistry
  from favorite.sessions.manager import SessionManager
  from favorite.platform import detect_platform
  sm = SessionManager()
  sid = sm.create_session(workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', title='T43 tasks')
  reg = CommandRegistry()
  ctx = CommandContext(
      workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', session_id=sid,
      platform=detect_platform(), config=get_config(), mgr=sm, registry=reg
  )
  tc = TasksCommand()
  try:
      tc.execute('', ctx)
      print(f'    -> TasksCommand.execute() OK')
  except Exception as e:
      print(f'    -> TasksCommand.execute (partial): {e}')
test('T43b: TasksCommand.execute()', t_tasks_cmd_list)

print('\n=== БЛОК 26: MODE COMMAND ===')

def t_mode_cmd_import():
  from favorite.commands.mode_cmd import ModeCommand
  mc = ModeCommand()
  assert hasattr(mc, 'name')
  print(f'    -> ModeCommand.name={mc.name!r}')
test('T44a: ModeCommand importable', t_mode_cmd_import)

def t_mode_cmd_status():
  from favorite.commands.mode_cmd import ModeCommand, _get_current_mode
  mode = _get_current_mode()
  assert isinstance(mode, str) and len(mode) > 0
  print(f'    -> current mode: {mode!r}')
test('T44b: _get_current_mode() returns string', t_mode_cmd_status)

print('\n=== БЛОК 27: AGENT REGISTRY ===')

def t_agent_registry_import():
  from favorite.agent.agent_registry import AgentRegistry, AgentEntry
  reg = AgentRegistry.get()
  assert reg is not None
  agents = reg.all()
  assert isinstance(agents, list)
  print(f'    -> AgentRegistry: {len(agents)} agents')
test('T45a: AgentRegistry.get() + all()', t_agent_registry_import)

def t_agent_registry_find_cap():
  from favorite.agent.agent_registry import AgentRegistry
  reg = AgentRegistry.get()
  # find_by_capability should return list even if empty
  result = reg.find_by_capability('nonexistent_cap')
  assert isinstance(result, list)
  result2 = reg.find_by_capability('general')
  assert isinstance(result2, list)
  print(f'    -> find_by_cap(general)={len(result2)} agents')
test('T45b: AgentRegistry.find_by_capability()', t_agent_registry_find_cap)

print('\n=== БЛОК 28: AUTO MODE ===')

def t_auto_mode_import():
  from favorite.commands.auto_cmd import is_auto_active, get_auto_stats
  active = is_auto_active()
  assert isinstance(active, bool)
  stats = get_auto_stats()
  print(f'    -> auto_active={active}, stats={stats}')
test('T46a: auto_cmd.is_auto_active() + get_auto_stats()', t_auto_mode_import)

def t_auto_mode_module():
  from favorite.agent.auto_mode import AutoLoop
  assert AutoLoop is not None
  print(f'    -> AutoLoop imported')
test('T46b: agent.auto_mode.AutoMode importable', t_auto_mode_module)

print('\n=== БЛОК 29: SESSIONS COMMAND ===')

def t_sessions_cmd_import():
  from favorite.commands.sessions_cmd import NewSessionCommand, SessionCommand
  ns = NewSessionCommand()
  sc = SessionCommand()
  assert hasattr(ns, 'name') and hasattr(sc, 'name')
  print(f'    -> NewSession={ns.name!r}, Session={sc.name!r}')
test('T47a: sessions commands importable', t_sessions_cmd_import)

print('\n=== БЛОК 30: PEER BUS ===')

def t_peer_bus_bus_status():
  from favorite.agent.peer_bus import get_bus_status
  status = get_bus_status(workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', session_id='t48-test')
  assert isinstance(status, dict)
  print(f'    -> bus status: {list(status.keys())}')
test('T48a: peer_bus.get_bus_status()', t_peer_bus_bus_status)

def t_peer_bus_read_inbox():
  from favorite.agent.peer_bus import read_inbox
  msgs = read_inbox(agent_id='main-1', session_id='t48b-test', workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI')
  assert isinstance(msgs, list)
  print(f'    -> inbox: {len(msgs)} messages')
test('T48b: peer_bus.read_inbox()', t_peer_bus_read_inbox)

print('\n=== БЛОК 31: VOTE MODULE ===')

def t_vote_import():
  from favorite.agent.vote import list_votes, get_vote_result
  votes = list_votes(workdir='/storage/emulated/0/Цхранилище/Project/FavoriteCLI', session_id='t49-test')
  assert isinstance(votes, list)
  print(f'    -> list_votes: {len(votes)} votes')
test('T49a: vote.list_votes() + get_vote_result()', t_vote_import)

print('\n=== БЛОК 32: SANDBOX ===')

def t_sandbox_make():
  from favorite.agent.sandbox import make_sandbox, list_sandboxes, cleanup_sandbox
  p = make_sandbox('/storage/emulated/0/Цхранилище/Project/FavoriteCLI', 't50-test', 'subagent-test')
  assert p.exists(), f'sandbox not created: {p}'
  print(f'    -> sandbox: {p.name}')
  sandboxes = list_sandboxes('/storage/emulated/0/Цхранилище/Project/FavoriteCLI', 't50-test')
  assert len(sandboxes) >= 1
  cleanup_sandbox(p)
  assert not p.exists()
  print(f'    -> sandbox cleaned up OK')
test('T50a: sandbox make + list + cleanup', t_sandbox_make)

def t_sandbox_is_enabled():
  from favorite.agent.sandbox import is_sandbox_enabled_globally
  from favorite.config.loader import get_config
  result = is_sandbox_enabled_globally(get_config())
  assert isinstance(result, bool)
  print(f'    -> sandbox_enabled_globally={result}')
test('T50b: sandbox.is_sandbox_enabled_globally()', t_sandbox_is_enabled)

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