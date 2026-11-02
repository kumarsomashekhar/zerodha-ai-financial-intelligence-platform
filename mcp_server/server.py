"""MCP server: offers the portfolio, market, news and analytics tools to any MCP-compatible AI app.
Run from the project root:  python -m mcp_server.server
(Never use print() here: a stdio server's output is reserved for the protocol.)"""
from mcp.server.fastmcp import FastMCP

from mcp_server.tools import analytics_tools, market_tools, news_tools, portfolio_tools

mcp = FastMCP("zerodha-portfolio-intelligence")

# portfolio tools
mcp.tool()(portfolio_tools.list_portfolios)
mcp.tool()(portfolio_tools.get_portfolio_metrics)
mcp.tool()(portfolio_tools.get_risk_alerts)
# market, news and analytics tools
mcp.tool()(market_tools.get_stock_price_summary)
mcp.tool()(news_tools.get_recent_news)
mcp.tool()(analytics_tools.get_benchmark_comparison)

if __name__ == "__main__":
    mcp.run(transport="stdio")