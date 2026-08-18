"""Standalone MCP entry point exposing the same validated booking tools."""

from mcp.server.fastmcp import FastMCP

from .mcp_tools import (
    cancel_reservation,
    check_availability,
    create_reservation,
    get_my_reservations,
    list_resources,
)

mcp = FastMCP("campus-booking")

mcp.tool()(list_resources)
mcp.tool()(check_availability)
mcp.tool()(create_reservation)
mcp.tool()(get_my_reservations)
mcp.tool()(cancel_reservation)


if __name__ == "__main__":
    mcp.run()
