import os
import httpx
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

NOTION_MCP_URL = "https://mcp.notion.com/mcp" # Official endpoint from docs

class NotionMCPClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.session = None
        self._exit_stack = None
        
    async def connect(self):
        """
        Connects to the Notion MCP server using SSE.
        """
        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "Mentoring-CRM-Client/1.0"
        }
        
        # Connect to SSE
        sse = await self._exit_stack.enter_async_context(
            sse_client(NOTION_MCP_URL, headers=headers)
        )
        
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(sse[0], sse[1])
        )
        
        await self.session.initialize()
        print("Connected to Notion MCP Server successfully.")

    async def close(self):
        if self._exit_stack:
            await self._exit_stack.aclose()

    async def get_tools(self):
        """Retrieve available Notion tools."""
        if not self.session:
            raise RuntimeError("Not connected")
        return await self.session.list_tools()
        
    async def call_tool(self, tool_name: str, arguments: dict):
        """Execute a specific Notion tool."""
        if not self.session:
            raise RuntimeError("Not connected")
        return await self.session.call_tool(tool_name, arguments)
