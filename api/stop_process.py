from helpers.api import ApiHandler, Input, Output, Request, Response
from helpers.print_style import PrintStyle


class StopProcess(ApiHandler):
    """Stop/cancel the currently running agent process in a given context."""

    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", "")

        context = self.use_context(ctxid)

        was_running = context.is_running()

        if was_running:
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
