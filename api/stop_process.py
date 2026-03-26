import os
import signal
import asyncio
from helpers.api import ApiHandler, Input, Output, Request, Response
from helpers.print_style import PrintStyle


class StopProcess(ApiHandler):
    """Stop/cancel the currently running agent process in a given context.
    
    Also sends SIGINT to active terminal sessions to interrupt running
    commands and prevent ghost child processes (e.g. pager, less).
    """

    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", "")

        context = self.use_context(ctxid)

        was_running = context.is_running()

        if was_running:
            # 1. Interrupt all active terminal sessions to kill child processes
            await self._interrupt_terminal_sessions(context)

            # 2. Kill the main agent DeferredTask
            context.kill_process()
            context.paused = False

            msg = "\u26d4 Process stopped by user."
            context.log.log(type="warning", content=msg)

            PrintStyle(
                background_color="#E74C3C", font_color="white", bold=True, padding=True
            ).print(f"Process stopped by user in context: {context.id}")

        return {
            "ok": True,
            "message": "Process stopped successfully." if was_running else "No process is currently running.",
            "was_running": was_running,
        }

    async def _interrupt_terminal_sessions(self, context) -> None:
        """Send Ctrl+C to all active terminal sessions and kill their child processes."""
        try:
            # Access the agent's code_execution_tool state
            agent = context.streaming_agent or context.agent0
            if not agent:
                return

            state = agent.get_data("_cet_state")
            if not state or not hasattr(state, "shells"):
                return

            for shell_id, shell_wrap in state.shells.items():
                try:
                    session = shell_wrap.session  # LocalInteractiveSession or SSH
                    tty = getattr(session, "session", None)  # TTYSession

                    if tty and hasattr(tty, "_proc") and tty._proc:
                        proc = tty._proc
                        pid = getattr(proc, "pid", None)

                        if pid:
                            # Kill all child processes of the shell
                            self._kill_process_tree(pid, signal.SIGKILL)

                        # Also send Ctrl+C to the shell itself
                        if hasattr(tty, "send"):
                            try:
                                await asyncio.wait_for(
                                    tty.send("\x03"),  # Ctrl+C
                                    timeout=1.0
                                )
                            except (asyncio.TimeoutError, Exception):
                                pass

                except Exception as e:
                    PrintStyle(font_color="yellow").print(
                        f"Warning: could not interrupt session {shell_id}: {e}"
                    )

        except Exception as e:
            PrintStyle(font_color="yellow").print(
                f"Warning: error accessing terminal sessions: {e}"
            )

    def _kill_process_tree(self, parent_pid: int, sig: int = signal.SIGKILL) -> None:
        """Kill all child processes of the given PID (but not the shell itself)."""
        try:
            # Read child PIDs from /proc
            children = []
            for pid_dir in os.listdir("/proc"):
                if not pid_dir.isdigit():
                    continue
                try:
                    with open(f"/proc/{pid_dir}/stat", "r") as f:
                        stat = f.read().split()
                        ppid = int(stat[3])
                        if ppid == parent_pid:
                            child_pid = int(pid_dir)
                            children.append(child_pid)
                except (FileNotFoundError, PermissionError, IndexError, ValueError):
                    continue

            # Recursively kill children of children first
            for child_pid in children:
                self._kill_process_tree(child_pid, sig)
                try:
                    os.kill(child_pid, sig)
                    PrintStyle(font_color="cyan").print(
                        f"Killed child process {child_pid} of shell {parent_pid}"
                    )
                except ProcessLookupError:
                    pass  # Already gone
                except Exception as e:
                    PrintStyle(font_color="yellow").print(
                        f"Warning: could not kill PID {child_pid}: {e}"
                    )

        except Exception as e:
            PrintStyle(font_color="yellow").print(
                f"Warning: error scanning process tree for PID {parent_pid}: {e}"
            )
