#!/usr/bin/env python3
import asyncio
import sys
from typing import Any
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Fix Windows encoding for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

mcp_server = Server("weather-server")

async def fetch_weather_data(city: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
        try:
            url = f"https://wttr.in/{city}?format=j1"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = await client.get(url, headers=headers)
            print(f"DEBUG: wttr.in status {response.status_code}", file=sys.stderr)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API Error: {str(e)}", file=sys.stderr)
            raise Exception(f"Failed to fetch weather: {str(e)}")

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_current_weather",
            description="Get current weather conditions for a city",
            inputSchema={  # ← MUST be inputSchema (camelCase)
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="get_placeholder_posts",
            description="Fetch mock blog posts from JSONPlaceholder for testing",
            inputSchema={  # ← Fixed from input_schema
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of posts to fetch (1-100)",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 5
                    }
                }
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    if name == "get_current_weather":
        city = arguments.get("city")
        try:
            data = await fetch_weather_data(city)
            current = data["current_condition"][0]
            result = (
                f"Weather for {city}:\n"
                f"Temperature: {current['temp_C']}°C\n"
                f"Condition: {current['weatherDesc'][0]['value']}\n"
                f"Humidity: {current['humidity']}%"
            )
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    elif name == "get_placeholder_posts":
        limit = arguments.get("limit", 5)
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get("https://jsonplaceholder.typicode.com/posts")
                response.raise_for_status()
                posts = response.json()[:limit]
                
                formatted = "\n\n".join([
                    f"Post #{p['id']}: {p['title']}\n{p['body'][:100]}..." 
                    for p in posts
                ])
                return [TextContent(type="text", text=f"Fetched {len(posts)} posts:\n\n{formatted}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())