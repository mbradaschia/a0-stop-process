# Stop Process Plugin for Agent Zero

Adds a **Stop** button to the chat input actions bar (next to Pause Agent and Nudge) that cancels the currently running agent process in the active session and returns the agent to idle state.

## Why this plugin exists

Agent Zero has **Pause** and **Nudge** but no way to simply **cancel a wrong command and go idle**:

| Action | What it does | Agent state after |
|--------|-------------|-------------------|
| **Pause Agent** | Suspends the agent at the next checkpoint | Paused (resumes on Resume) |
| **Nudge** | Kills the current process and starts a new task with a nudge prompt | Running (new task) |
| **Stop (this plugin)** | Kills the current process and goes idle | **Idle (waiting for input)** |

The Stop button fills the gap: it fully terminates a wrong or unwanted command without pausing indefinitely or nudging (which re engages the agent).

## Features

- **Stop button** always visible in the bottom chat actions bar
- **Gray/disabled** when idle, **red/active** when a process is running
- Immediately **terminates** the running agent task
- Shows **"⛔ Process stopped by user."** warning message in the chat log
- **Instant UI reset**: input box returns to idle/waiting state immediately (no polling delay)
- **Ghost process prevention**: kills orphaned child OS processes (pager, less, etc.) spawned by terminal sessions
- **Context isolation**: only affects the active chat; other chats are never touched
- Toast notification confirming the action

## Installation

1. Copy the `stop_process` folder to `/a0/usr/plugins/`
2. Enable the plugin in **Settings** → **Plugins**
3. Refresh the page

Or install from the Plugin Hub in Agent Zero.

## How It Works

### Architecture Overview

The plugin consists of two parts: a **frontend UI component** injected into the chat input actions bar and a **backend API handler** that performs the actual process termination.

```
User clicks Stop button
        │
        ▼
┌─────────────────────────────────┐
│  Frontend (stop-button.html)    │
│  Sends POST to backend API      │
│  with current chat context ID   │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Backend (stop_process.py)      │
│  1. Resolve context via         │
│     self.use_context(ctxid)     │
│  2. Kill terminal child procs   │
│  3. context.kill_process()      │
│  4. context.paused = False      │
│  5. Log warning to chat         │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Frontend receives response     │
│  Sets running = false on store  │
│  Input box resets to idle       │
│  Toast notification shown       │
└─────────────────────────────────┘
```

### Frontend: stop-button.html

The HTML extension is injected into the `chat-input-bottom-actions-end` extension point, placing it alongside the existing Pause and Nudge buttons.

**Visual states:**
- When the agent is **idle**: button is grayed out (40% opacity, `not-allowed` cursor, disabled)
- When the agent is **running**: button turns **red** (#e74c3c), 80% opacity, clickable

**Reactive bindings** use Alpine.js:
- `:disabled="!$store.chats?.selectedContext?.running"` prevents clicking when idle
- `:class="{ 'stop-active': $store.chats?.selectedContext?.running }"` toggles visual state

**Immediate UI reset** after a successful stop:
- Imports `chatsStore` from the sidebar chats store
- Sets `chatsStore.selectedContext.running = false` directly (reactive, propagates instantly)
- Also triggers `globalThis.poll()` after 300ms as a safety fallback

### Backend: stop_process.py (API Handler)

The API handler follows the same pattern as the built in Pause and Nudge handlers:

```python
context = self.use_context(ctxid)   # Resolve context with proper thread locking
await self._interrupt_terminal_sessions(context)  # Kill ghost processes
context.kill_process()               # Cancel the DeferredTask
context.paused = False               # Ensure clean idle state
context.log.log(type="warning", content="⛔ Process stopped by user.")
```

**Key detail**: uses `self.use_context(ctxid)` (NOT `AgentContext.use()`) to ensure proper thread locking and context resolution, consistent with the Pause and Nudge handlers.

### Ghost Process Prevention

#### The Problem

When `context.kill_process()` is called, it cancels the Python `DeferredTask` (the asyncio Future). However, it does **not** terminate child OS processes spawned by `code_execution_tool` terminal sessions.

For example, if the agent runs `git log` in a terminal session, the shell spawns a `pager` process. When the DeferredTask is cancelled, the `pager` process becomes an orphan and keeps running at full CPU:

```
PID   COMMAND   CPU
18624 pager     90.9%   ← orphaned, consuming CPU after Stop
18716 pager     90.9%   ← orphaned, consuming CPU after Stop
```

#### The Solution

Before calling `context.kill_process()`, the handler runs `_interrupt_terminal_sessions()` which:

1. **Accesses the terminal state** via `agent.get_data("_cet_state")` to get all active shell sessions
2. **For each shell session**, gets the `TTYSession._proc.pid` (the shell's PID)
3. **Scans `/proc`** to find all child processes of that shell PID
4. **Recursively kills** the entire process tree (children of children first, then children) using `SIGKILL`
5. **Sends `Ctrl+C`** (`\x03`) to the shell itself to interrupt any running command

```
Shell (bash) PID 1234
├── git log PID 1235      ← killed by _kill_process_tree()
│   └── pager PID 1236    ← killed by _kill_process_tree()
└── (shell survives for future commands)
```

### Context Isolation

The Stop button **only affects the active chat**. This is guaranteed by the architecture:

| Layer | Scope |
|-------|-------|
| **Frontend** | Sends only the current chat's context ID via `globalThis.getContext()` |
| **Backend** | `self.use_context(ctxid)` retrieves only that specific `AgentContext` |
| **Task kill** | `context.kill_process()` kills only that context's `DeferredTask` |
| **Terminal cleanup** | `agent.get_data("_cet_state")` returns only that agent's terminal sessions |
| **Process tree kill** | Starts from shell PIDs of that agent only; other chats' PIDs are never reached |

Each chat has its own `AgentContext` (unique ID), its own `Agent` instance (`agent0`), its own terminal sessions, and its own `DeferredTask`. Clicking Stop in Chat A will **never** affect processes running in Chat B.

## File Structure

```
stop_process/
├── plugin.yaml                 # Plugin manifest
├── README.md                   # This file
├── LICENSE                     # MIT License
├── api/
│   ├── __init__.py             # Python module marker
│   └── stop_process.py         # Backend API handler
└── extensions/
    └── webui/
        └── chat-input-bottom-actions-end/
            └── stop-button.html  # Frontend UI component
```

## Requirements

Agent Zero v1.1+

## License

MIT
