#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server

A lightweight MCP server that communicates via JSON-RPC 2.0 over stdio.
Implements the Model Context Protocol specification for providing tools,
resources, and prompts to AI models.

Usage:
    python3 mcp_server.py

Connects to an MCP client (e.g., Claude, Codex) via stdin/stdout.
"""

import json
import sys
import logging
import traceback
from typing import Any, Callable

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("mcp-server")

# Protocol version
MCP_VERSION = "2025-03-26"


class JSONRPCError(Exception):
    """JSON-RPC error with code, message, and optional data."""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"[{code}] {message}")


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class MCPServer:
    """Model Context Protocol server.

    Dispatches incoming JSON-RPC requests to registered handlers
    for tools, resources, and prompts.

    Handlers are registered via the `tool`, `resource`, and `prompt`
    decorators or by calling `register_tool()`, `register_resource()`,
    `register_prompt()`.
    """

    def __init__(self, name: str = "mcp-server", version: str = "0.1.0"):
        self.name = name
        self.version = version
        self._tools: dict[str, dict[str, Any]] = {}
        self._resources: dict[str, dict[str, Any]] = {}
        self._prompts: dict[str, dict[str, Any]] = {}
        self._initialized = False

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable,
    ):
        """Register a tool that the model can call."""
        self._tools[name] = {
            "description": description,
            "inputSchema": input_schema,
            "_handler": handler,
        }

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str,
        handler: Callable,
    ):
        """Register a resource (static or dynamic) for the model to read."""
        self._resources[uri] = {
            "name": name,
            "description": description,
            "mimeType": mime_type,
            "_handler": handler,
        }

    def register_prompt(
        self,
        name: str,
        description: str,
        arguments: list[dict[str, Any]],
        handler: Callable,
    ):
        """Register a prompt template for the model or user to use."""
        self._prompts[name] = {
            "description": description,
            "arguments": arguments,
            "_handler": handler,
        }

    def tool(self, name: str, description: str, input_schema: dict[str, Any]):
        """Decorator to register a tool handler."""
        def decorator(func):
            self.register_tool(name, description, input_schema, func)
            return func
        return decorator

    def resource(self, uri: str, name: str, description: str,
                 mime_type: str = "text/plain"):
        """Decorator to register a resource handler."""
        def decorator(func):
            self.register_resource(uri, name, description, mime_type, func)
            return func
        return decorator

    def prompt(self, name: str, description: str,
               arguments: list[dict[str, Any]] | None = None):
        """Decorator to register a prompt handler."""
        def decorator(func):
            self.register_prompt(name, description, arguments or [], func)
            return func
        return decorator

    # ------------------------------------------------------------------
    # Protocol message handling
    # ------------------------------------------------------------------

    def _send(self, msg: dict[str, Any]):
        """Send a JSON-RPC message to the client."""
        line = json.dumps(msg)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def _send_error(self, id: Any, code: int, message: str,
                    data: Any = None):
        """Send a JSON-RPC error response."""
        self._send({
            "jsonrpc": "2.0",
            "id": id,
            "error": {"code": code, "message": message, "data": data},
        })

    def _send_result(self, id: Any, result: Any):
        """Send a successful JSON-RPC response."""
        self._send({
            "jsonrpc": "2.0",
            "id": id,
            "result": result,
        })

    def _send_notification(self, method: str, params: dict[str, Any] | None = None):
        """Send a JSON-RPC notification (no id)."""
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)

    def _handle_request(self, msg: dict[str, Any]):
        """Process one incoming JSON-RPC request."""
        req_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {}) or {}

        log.debug(f"Request: {method} id={req_id}")

        # --- lifecycle ---
        if method == "initialize":
            client_info = params.get("clientInfo", {})
            client_name = client_info.get("name", "unknown")
            client_version = client_info.get("version", "0.0.0")
            log.info(f"Client connected: {client_name} v{client_version}")

            capabilities = params.get("capabilities", {})
            log.debug(f"Client capabilities: {json.dumps(capabilities)}")

            self._initialized = True
            self._send_result(req_id, {
                "protocolVersion": MCP_VERSION,
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {
                    "name": self.name,
                    "version": self.version,
                },
            })
            return

        if method == "notifications/initialized":
            log.info("Client initialized notification received")
            return

        # --- tools ---
        if method == "tools/list":
            tool_list = [
                {"name": name, "description": info["description"],
                 "inputSchema": info["inputSchema"]}
                for name, info in self._tools.items()
            ]
            self._send_result(req_id, {"tools": tool_list})
            return

        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {}) or {}
            tool = self._tools.get(tool_name)
            if not tool:
                self._send_error(req_id, METHOD_NOT_FOUND,
                                 f"Unknown tool: {tool_name}")
                return
            try:
                result = tool["_handler"](**arguments)
                self._send_result(req_id, {
                    "content": [
                        {"type": "text", "text": str(result)}
                    ],
                    "isError": False,
                })
            except Exception as e:
                log.error(f"Tool {tool_name} error: {e}\n{traceback.format_exc()}")
                self._send_result(req_id, {
                    "content": [
                        {"type": "text", "text": f"Error: {e}"}
                    ],
                    "isError": True,
                })
            return

        # --- resources ---
        if method == "resources/list":
            resource_list = [
                {"uri": uri, "name": info["name"],
                 "description": info["description"],
                 "mimeType": info["mimeType"]}
                for uri, info in self._resources.items()
            ]
            self._send_result(req_id, {"resources": resource_list})
            return

        if method == "resources/read":
            uri = params.get("uri", "")
            resource = self._resources.get(uri)
            if not resource:
                self._send_error(req_id, METHOD_NOT_FOUND,
                                 f"Unknown resource: {uri}")
                return
            try:
                content = resource["_handler"]()
                self._send_result(req_id, {
                    "contents": [
                        {"uri": uri, "mimeType": resource["mimeType"],
                         "text": str(content)}
                    ],
                })
            except Exception as e:
                log.error(f"Resource {uri} error: {e}\n{traceback.format_exc()}")
                self._send_error(req_id, INTERNAL_ERROR, str(e))
            return

        # --- prompts ---
        if method == "prompts/list":
            prompt_list = [
                {"name": name, "description": info["description"],
                 "arguments": info["arguments"]}
                for name, info in self._prompts.items()
            ]
            self._send_result(req_id, {"prompts": prompt_list})
            return

        if method == "prompts/get":
            prompt_name = params.get("name", "")
            arguments = params.get("arguments", {}) or {}
            prompt = self._prompts.get(prompt_name)
            if not prompt:
                self._send_error(req_id, METHOD_NOT_FOUND,
                                 f"Unknown prompt: {prompt_name}")
                return
            try:
                messages = prompt["_handler"](**arguments)
                self._send_result(req_id, {
                    "messages": messages,
                })
            except Exception as e:
                log.error(f"Prompt {prompt_name} error: {e}\n{traceback.format_exc()}")
                self._send_error(req_id, INTERNAL_ERROR, str(e))
            return

        # unknown method
        self._send_error(req_id, METHOD_NOT_FOUND,
                         f"Method not found: {method}")

    def _handle_message(self, raw: str):
        """Parse and handle a single JSON-RPC message."""
        if not raw.strip():
            return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            log.error(f"Parse error: {e}")
            self._send({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": PARSE_ERROR, "message": "Parse error"},
            })
            return

        # Notification (no id)
        if "id" not in msg:
            method = msg.get("method", "")
            params = msg.get("params", {}) or {}
            log.debug(f"Notification: {method}")
            if method == "notifications/initialized":
                self._initialized = True
                log.info("Client initialized (notification)")
            return

        try:
            self._handle_request(msg)
        except Exception as e:
            log.error(f"Unhandled error: {e}\n{traceback.format_exc()}")
            self._send_error(
                msg["id"], INTERNAL_ERROR, "Internal server error",
            )

    def run(self):
        """Start the server: read JSON-RPC messages from stdin."""
        log.info(f"Starting {self.name} v{self.version} (MCP {MCP_VERSION})")

        # Send a startup notification
        self._send_notification("server/started", {
            "name": self.name,
            "version": self.version,
        })

        for line in sys.stdin:
            if not line.strip():
                continue
            self._handle_message(line)

        log.info("Server shutting down (stdin closed)")


# ======================================================================
# Example / demo tools, resources, and prompts
# ======================================================================

def create_demo_server() -> MCPServer:
    """Create an MCPServer with a set of example tools/resources/prompts."""
    server = MCPServer(name="demo-mcp-server", version="0.1.0")

    # ---- Tools ----

    @server.tool(
        name="calculator",
        description="Perform basic arithmetic operations",
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "Math operation to perform",
                },
                "a": {"type": "number", "description": "First operand"},
                "b": {"type": "number", "description": "Second operand"},
            },
            "required": ["operation", "a", "b"],
        },
    )
    def calculator(operation: str, a: float, b: float) -> str:
        ops = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else "undefined (division by zero)",
        }
        fn = ops.get(operation)
        if fn is None:
            return f"Unknown operation: {operation}"
        result = fn(a, b)
        return f"{a} {operation} {b} = {result}"

    @server.tool(
        name="echo",
        description="Echo back the input text",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to echo"},
            },
            "required": ["text"],
        },
    )
    def echo(text: str) -> str:
        return f"Echo: {text}"

    @server.tool(
        name="current_time",
        description="Get the current date and time in ISO format",
        input_schema={
            "type": "object",
            "properties": {},
        },
    )
    def current_time() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    @server.tool(
        name="greet",
        description="Generate a personalized greeting message",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the person"},
                "title": {
                    "type": "string",
                    "enum": ["Mr.", "Ms.", "Dr.", "Prof.", ""],
                    "description": "Optional title",
                },
            },
            "required": ["name"],
        },
    )
    def greet(name: str, title: str = "") -> str:
        prefix = f"{title} " if title else ""
        return f"Hello, {prefix}{name}! Welcome to MCP."

    # ---- Resources ----

    @server.resource(
        uri="server://info",
        name="Server Information",
        description="Metadata about this MCP server",
        mime_type="application/json",
    )
    def server_info() -> str:
        return json.dumps({
            "name": server.name,
            "version": server.version,
            "protocol": MCP_VERSION,
            "language": "Python 3",
        }, indent=2)

    # ---- Prompts ----

    @server.prompt(
        name="code_review",
        description="Ask the model to review a code snippet",
        arguments=[
            {
                "name": "language",
                "description": "Programming language of the code",
                "required": True,
            },
            {
                "name": "code",
                "description": "The code to review",
                "required": True,
            },
        ],
    )
    def code_review(language: str, code: str) -> list[dict[str, Any]]:
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Please review this {language} code:\n\n```{language}\n{code}\n```",
                },
            },
        ]

    return server


# ======================================================================
# Entry point
# ======================================================================

if __name__ == "__main__":
    # Enable debug logging with --debug flag
    if "--debug" in sys.argv:
        log.setLevel(logging.DEBUG)

    server = create_demo_server()
    try:
        server.run()
    except KeyboardInterrupt:
        log.info("Server stopped by user")
        sys.exit(0)
