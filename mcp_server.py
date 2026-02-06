#!/usr/bin/env python3
"""
Enhanced MCP Server with Pesticide and Seed Information Tool
"""
import asyncio
import json
import sys
from typing import Any
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Set encoding for Windows to prevent Emoji crashes
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Initialize MCP server
mcp_server = Server("agricultural-server")

async def fetch_weather_data(city: str) -> dict:
    """Fetch weather data from wttr.in API"""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
        try:
            url = f"https://wttr.in/{city}?format=j1"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = await client.get(url, headers=headers)
            print(f"DEBUG: wttr.in returned {response.status_code}", file=sys.stderr)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API Error: {str(e)}", file=sys.stderr)
            raise Exception(f"Failed to fetch weather data: {str(e)}")

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """Register all available tools"""
    return [
        Tool(
            name="get_current_weather",
            description="Get current weather conditions for a specific city or location. Use this when users ask about weather, temperature, or climate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Name of the city to get weather for"
                    }
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="get_placeholder_posts",
            description="Fetch mock blog posts from JSONPlaceholder API. Use this when users ask about posts, blogs, or articles.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of posts to fetch (1-100)",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 5
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_pesticide_seed_info",
            description="Get information about pesticides and seeds for agricultural purposes. Use this when users ask about farming, agriculture, pesticides, seeds, crops, or planting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What the user wants to know about (e.g., 'organic pesticides', 'wheat seeds', 'tomato farming')",
                        "default": "general information"
                    }
                },
                "required": []
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute the requested tool"""
    
    if name == "get_current_weather":
        city = arguments.get("city")
        try:
            data = await fetch_weather_data(city)
            current = data["current_condition"][0]
            formatted = (
                f"🌤️  Current Weather in {city}:\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Temperature: {current['temp_C']}°C\n"
                f"Condition: {current['weatherDesc'][0]['value']}\n"
                f"Humidity: {current['humidity']}%\n"
                f"Wind Speed: {current.get('windspeedKmph', 'N/A')} km/h"
            )
            return [TextContent(type="text", text=formatted)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching weather: {str(e)}")]

    elif name == "get_placeholder_posts":
        limit = arguments.get("limit", 5)
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get("https://jsonplaceholder.typicode.com/posts")
                response.raise_for_status()
                posts = response.json()[:limit]
                
                formatted_posts = [
                    f"📝 Post #{p['id']}: {p['title']}\n{p['body'][:100]}..." 
                    for p in posts
                ]
                
                result = f"📚 Fetched {len(posts)} blog posts:\n\n" + "\n\n".join(formatted_posts)
                return [TextContent(type="text", text=result)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error fetching posts: {str(e)}")]
    
    elif name == "get_pesticide_seed_info":
        query = arguments.get("query", "general information")
        
        # This is a placeholder - in production, you'd fetch from a real database
        response = (
            f"🌾 Welcome to Pesticide and Seed Information Service! 🌱\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Query: {query}\n\n"
            f"I will fetch comprehensive information about seeds and pesticides for you!\n\n"
            f"📋 Services Available:\n"
            f"  • Seed recommendations for different crops\n"
            f"  • Organic and chemical pesticide information\n"
            f"  • Seasonal planting guides\n"
            f"  • Pest identification and treatment\n"
            f"  • Fertilizer recommendations\n"
            f"  • Crop rotation strategies\n\n"
            f"🔜 Coming Soon:\n"
            f"  - Real-time pest alerts\n"
            f"  - Seed supplier database\n"
            f"  - Pesticide safety guidelines\n"
            f"  - Crop yield predictions\n\n"
            f"💡 Tip: Ask me about specific crops, pests, or farming techniques!"
        )
        
        return [TextContent(type="text", text=response)]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Start the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())