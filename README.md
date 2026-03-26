# Stop Process Plugin for Agent Zero

Adds a **Stop** button to the chat input actions bar (next to Pause Agent and Nudge) that cancels the currently running agent process in the active session.

## Features

- **Stop button** always visible in the bottom actions bar
- **Gray/disabled** when no process is running, **red/active** when a process is running
- Immediately **terminates** the running agent task (unlike Pause, which only suspends)
- Shows **"⛔ Process stopped by user."** warning message in the chat log
- **Instant UI reset**: input box returns to idle/waiting state immediately (no polling delay)
- Toast notification confirming the action

## How It Works

| Action | Pause Agent | Nudge | **Stop (this plugin)** |
|--------|-------------|-------|------------------------|
| Effect | Suspends agent at next checkpoint | Kills + restarts with nudge message | Kills + goes idle |
| Agent state after | Paused (resumes on Resume) | Running (new task) | **Idle (waiting for input)** |

The Stop button fills a gap: there was no way to simply cancel a wrong command and return to idle without pausing indefinitely or nudging (which re engages the agent).

## Installation

1. Copy the `stop_process` folder to `/a0/usr/plugins/`
2. Enable the plugin in **Settings** → **Plugins**
3. Refresh the page

Or install from the Plugin Hub in Agent Zero.

## File Structure

```
stop_process/
├── plugin.yaml
├── README.md
├── LICENSE
├── api/
│   ├── __init__.py
│   └── stop_process.py
└── extensions/
    └── webui/
        └── chat-input-bottom-actions-end/
            └── stop-button.html
```

## Requirements

Agent Zero v1.1+

## License

MIT
