"""Starts the MCP server and calls each tool, the way an AI app would."""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]

CALLS = [
    ("list_portfolios", {}),
    ("get_stock_price_summary", {"symbol": "INFY"}),
    ("get_benchmark_comparison", {"portfolio_id": "diversified"}),
    ("get_recent_news", {"symbol": "TCS", "limit": 2}),
    ("get_benchmark_comparison", {"portfolio_id": "volatile_smallcap"}),
]


async def main():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server.server"], cwd=str(ROOT)
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools offered by the server:")
            for t in tools.tools:
                print(" -", t.name)
            for name, args in CALLS:
                result = await session.call_tool(name, args)
                print(f"\n{name} {args}:")
                for block in result.content:
                    print(block.text)


asyncio.run(main())