# FavoriteCLI

Python CLI AI-agent for Termux/Android. Inspired by Claude Code.

**Color scheme:** white + orange  
**Entry point:** `python favorite.py`  
**Architecture:** SOLID — each module has one job

---

## Quick Start (Termux)

```bash
pkg install python tmux git
pip install -r requirements.txt
python favorite.py
```

## Quick Start (Linux/Replit)

```bash
pip install -r requirements.txt
python favorite.py
```

---

## Project Structure

```
favorite.py              # entry point
favorite/
  app.py                 # DI container + run loop
  platform.py            # IPlatform (TermuxPlatform / LinuxFakePlatform)
  ui/                    # welcome, chat, prompt, theme, spinner
  commands/              # ICommand implementations
  api/                   # IChatProvider (FavoriteAPI, OpenRouter, NVIDIA)
  agent/                 # tags parser, executor, llm, model_router, sub_agent
  skills/                # web_search, fetch_url, fs_tools
  sessions/              # session CRUD + stats
  tasks/                 # task manager (CRUD)
  github/                # GitHub REST API push
  config/                # loader.py
  memory/                # Favorite.md hot-reload
  bridge/                # Telegram URL bridge
config/
  api_keys.json          # API keys
  github.json            # GitHub token + repo
Favorite.md              # permanent AI memory (system prompt)
sessions/                # per-session data
  <session_id>/
    meta.json
    history.jsonl
    tasks.json
    plan.txt
    context_summary.md
```

---

## API Providers

| Provider | Notes |
|---|---|
| **OpenRouter** | Default. Supports streaming SSE. Default model: `qwen/qwen3-coder:free` |
| **FavoriteAPI** | Local Telegram-bridge to Gemini. URL: `http://127.0.0.1:5005` |
| **NVIDIA NIM** | `https://integrate.api.nvidia.com/v1` — OpenAI-compatible |
| **VoidAI** | WebSearch skill (`perplexity/sonar` + DuckDuckGo fallback) |

---

## Commands

| Command | Description |
|---|---|
| `/plan` | Discuss task interactively, write plan.txt to session |
| `/build` | Read plan.txt, execute tags, push to GitHub |
| `/agents [list\|spawn\|kill]` | Manage main agent + sub-agents |
| `/skills` | List and configure skills |
| `/tasks [list\|add\|done\|todo\|progress\|del]` | Session task manager |
| `/memory [edit]` | View/edit Favorite.md |
| `/usage` | Session stats: requests, tokens, duration, model |
| `/doctor` | Diagnose: API keys, network, workdir, Favorite.md |
| `/recap [N]` | Compact digest of last N exchanges |
| `/compact` | Compress history to context_summary.md |
| `/session` | List saved sessions |
| `/new session` | Start a new session |
| `/models` | List available models |
| `/Favorite API` | Manage FavoriteAPI keys + TG bridge |
| `/OpenRouter API` | Manage OpenRouter keys + model picker |

---

## Agent Tag Reference

Tags are written by the AI in its responses and executed automatically.

| Tag | Syntax | Effect |
|---|---|---|
| `STEP` | `≪STEP≫text≪/STEP≫` | Status line shown to user |
| `THINK` | `≪THINK≫...≪/THINK≫` | Internal reasoning — hidden |
| `SHELL_RAW` | `≪SHELL_RAW≫cmd≪/SHELL_RAW≫` | Run shell command, return output |
| `SHELL_BG` | `≪SHELL_BG≫cmd≪/SHELL_BG≫` | Run in background (no output) |
| `READ_FILE` | `≪READ_FILE:path=rel/path≫` | Read file, return content to AI |
| `WRITE_FILE` | `≪WRITE_FILE:path=rel/path≫content≪/WRITE_FILE≫` | Write file silently |
| `ASK_USER` | `≪ASK_USER:text≫question≪/ASK_USER≫` | Prompt user, return answer |
| `WRITE_FAV` | `≪WRITE_FAV≫content≪/WRITE_FAV≫` | Update Favorite.md |
| `WRITE_CTX` | `≪WRITE_CTX≫content≪/WRITE_CTX≫` | Write context_summary.md |
| `WRITE_PLAN` | `≪WRITE_PLAN≫content≪/WRITE_PLAN≫` | Write plan.txt |
| `GIT_PUSH` | `≪GIT_PUSH:msg=message≫files≪/GIT_PUSH≫` | Push to GitHub |
| `SKILL` | `≪SKILL:name=web_search≫query≪/SKILL≫` | Call a skill |
| `CONTINUE` | `≪CONTINUE≫` | Request next step from AI |
| `POLL` | `≪POLL≫question≪/POLL≫` | Ask user, continue loop |
| `SLEEP` | `≪SLEEP:seconds=2≫` | Wait N seconds |
| `SUB_AGENT` | `≪SUB_AGENT:role=debugger≫task≪/SUB_AGENT≫` | Spawn sub-agent |
| `ADD_TASK` | `≪ADD_TASK≫title≪/ADD_TASK≫` | Add task to session list |
| `UPDATE_TASK` | `≪UPDATE_TASK:id=X:status=done≫` | Update task status |
| `COMPLETE_TASK` | `≪COMPLETE_TASK≫id≪/COMPLETE_TASK≫` | Mark task done |
| `LIST_TASKS` | `≪LIST_TASKS≫` | Return task list to AI |

---

## GitHub Push

The agent pushes via GitHub REST API (no git CLI needed).  
Config: `config/github.json`

```json
{
  "token": "ghp_...",
  "owner": "your-username",
  "repo": "FavoriteCLI",
  "branch": "main"
}
```

---

## Platform Detection

Set `FAVORITE_PLATFORM=termux` or `FAVORITE_PLATFORM=linux` to override auto-detection.  
Auto-detect checks for Termux `$PREFIX` path.

---

## Session Export

Press **ESC then END** during chat to export the full session to a text file  
(path: `/storage/emulated/0/.../session.txt` on Android).
