"""One cancellable generation job; commit through the normal graph/history path."""
import asyncio
from copy import deepcopy
import logging
import os

from .protocol import encode, event


class Generation:
    def __init__(self, router):
        self.router = router
        self.task = None
        self.preview = None
        self.mode = "generate"
        self.state = {"status": "idle", "message": "", "nodes": 0, "mode": self.mode}

    async def report(self, status, message, nodes=0):
        self.state = {"status": status, "message": message, "nodes": nodes, "mode": self.mode}
        if status != "running":
            self.preview = None
        handlers = self.router.handlers
        await handlers.broadcast(event("jev.update", self.state, handlers.runtime.revision))

    async def publish_preview(self, runtime):
        # Only accepted structure/ports are published; audition arrays stay private.
        self.preview = {"graph": {
            "nodes": [{**node, "parameters": {}} for node in runtime.graph["nodes"]],
            "connections": deepcopy(runtime.graph["connections"])},
            "nodes": [{"id": node.name(), "type": node.nodeName, "ports": runtime.describe(node)["ports"]}
                      for node in runtime.nodes.values()]}
        handlers = self.router.handlers
        await handlers.broadcast(event("jev.preview", self.preview, handlers.runtime.revision))

    async def start(self, session, payload):
        from ai.template_generator.agent import Generator
        if self.task is not None and not self.task.done():
            raise ValueError("Jev is already generating a graph")
        prompt = payload["prompt"]
        if type(prompt) is not str or not prompt.strip() or len(prompt) > 16000:
            raise ValueError("Provide a prompt between 1 and 16000 characters")
        mode = payload.get("mode", "generate")
        if mode not in ("generate", "edit"):
            raise ValueError("Jev mode must be generate or edit")
        if not os.environ.get("OPENCODE_API_KEY"):
            raise ValueError("Set OPENCODE_API_KEY in the backend .env file")
        source = deepcopy(self.router.handlers.runtime.graph)
        self.mode = mode
        self.preview = None
        self.task = asyncio.create_task(self.run(Generator(self.router.handlers.runtime.catalog), session, prompt.strip(), source))
        await self.report("running", "Starting Jev")
        return self.state

    async def cancel(self, session=None, payload=None):
        async with self.router.edit_lock:
            if self.task is not None and not self.task.done():
                self.task.cancel()
                await asyncio.gather(self.task, return_exceptions=True)
        return self.state

    async def run(self, generator, session, prompt, source):
        handlers = self.router.handlers
        try:
            graph = await generator.generate(prompt, source, self.report, self.publish_preview, self.mode)
            async with self.router.edit_lock:
                if encode(handlers.runtime.graph) != encode(source):
                    raise ValueError("The graph changed during generation; generate again to keep your edits")
                inverse = self.router.history.capture("graph.load", {})
                await handlers._load(graph, replace=self.mode == "generate")
                self.router.history.record(inverse, session, "graph.load", {})
                await handlers.broadcast(event("history.update", {"canUndo": True}, handlers.runtime.revision))
                await self.report("complete", "Graph loaded · Undo restores the previous graph", len(graph["nodes"]))
        except asyncio.CancelledError:
            await self.report("cancelled", "Generation cancelled")
        except Exception as error:
            logging.getLogger(__name__).exception("Jev generation failed")
            await self.report("error", str(error))
