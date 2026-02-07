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

# ============================================================================
# CITRUS KNOWLEDGE BASE - RAG DATA
# ============================================================================

CITRUS_KNOWLEDGE_BASE = """
Pesticide Practices for Citrus Cultivation in India
Focus Crop: Mosambi (Sweet Lemon)

1. Introduction: Importance of Pest Management in Citrus
Citrus crops such as Mosambi (Sweet Lemon) are economically important fruit crops cultivated widely across India, especially in Maharashtra, Telangana, Andhra Pradesh, Madhya Pradesh, and parts of North India. These crops are high-value, long-duration perennial plants, meaning that pest and disease pressure accumulates over multiple seasons if not managed properly.

Pests in citrus affect:
- Leaf health (photosynthesis)
- Flowering and fruit set
- Fruit quality and size
- Tree longevity and yield consistency

Because citrus orchards remain productive for 15–25 years, improper pesticide use can lead to pest resistance, soil and water contamination, and loss of beneficial insects.

2. Major Insect Pests in Mosambi and Commonly Used Pesticides

2.1 Citrus Psylla (Diaphorina citri)
Nature of Damage: Sucks sap from tender leaves and shoots, causes leaf curling and stunted growth, major vector of Citrus Greening (HLB) disease
Season of Occurrence: Peak during new flush (Feb–March, July–September)
Commonly Used Pesticides: Imidacloprid 17.8% SL, Thiamethoxam 25% WG, Acetamiprid 20% SP
Application Notes: Avoid spraying during flowering, prefer soil drenching to reduce impact on pollinators, rotate molecules to prevent resistance

2.2 Citrus Leaf Miner
Nature of Damage: Larvae create zig-zag tunnels in young leaves, severely affects nursery plants and young orchards, increases susceptibility to citrus canker
Season of Occurrence: High during monsoon and post-monsoon flush
Commonly Used Pesticides: Abamectin 1.9% EC, Spinosad 45% SC, Emamectin benzoate 5% SG
Integrated Practice: Spray only during active leaf flush, avoid repeated spraying on mature leaves

2.3 Aphids
Nature of Damage: Sap sucking leads to leaf distortion, produces honeydew encouraging sooty mold, transmits viral diseases
Commonly Used Pesticides: Dimethoate 30% EC, Imidacloprid 17.8% SL, Flonicamid 50% WG
Precautions: Monitor colonies before spraying, avoid overuse of organophosphates

2.4 Mealybugs
Nature of Damage: Attacks shoots, leaves, fruits, and roots, causes fruit drop and plant weakening, severe infestation can kill young trees
Commonly Used Pesticides: Chlorpyrifos 20% EC (restricted use, soil application), Buprofezin 25% SC, Spirotetramat 15.31% OD
Additional Measures: Use sticky bands on trunks, control ants that spread mealybugs

2.5 Red Spider Mites
Nature of Damage: Yellow speckling on leaves, leaf bronzing and premature leaf fall, reduced fruit size and juice content
Commonly Used Acaricides: Propargite 57% EC, Fenazaquin 10% EC, Hexythiazox 5% EC
Best Practice: Spray early during infestation, ensure proper spray coverage on leaf undersides

3. Major Diseases and Fungicide Usage in Citrus

3.1 Citrus Canker (Bacterial Disease)
Symptoms: Raised corky lesions on leaves, stems, and fruits, fruit drop and market rejection
Common Chemicals Used: Copper oxychloride 50% WP, Streptocycline (with copper fungicide), Bordeaux mixture (1%)
Management Strategy: Avoid spraying antibiotics repeatedly, focus on sanitation and pruning

3.2 Phytophthora (Root Rot, Gummosis)
Symptoms: Gum oozing from trunk, root decay and wilting, sudden plant death in severe cases
Common Fungicides: Metalaxyl + Mancozeb, Fosetyl-Al, Copper-based fungicides (soil drench)
Preventive Measures: Proper drainage, avoid water stagnation near trunk

3.3 Powdery Mildew
Symptoms: White powdery growth on leaves and flowers, reduced fruit set
Common Fungicides: Sulphur 80% WP, Hexaconazole 5% EC, Penconazole

4. Safe Pesticide Application Practices for Farmers

4.1 Dosage and Timing
- Always follow label-recommended dose
- Spray during early morning or late evening
- Avoid spraying during strong winds or rain

4.2 Spraying Equipment
- Use cone nozzle for uniform coverage
- Calibrate sprayers regularly
- Separate sprayers for herbicides and insecticides

4.3 Pre-Harvest Interval (PHI)
- Respect PHI to avoid pesticide residues
- Important for export-quality fruits

5. Resistance Management and Pesticide Rotation
Overuse of the same pesticide leads to resistance development, making future control difficult.

Best Practices:
- Rotate pesticides with different modes of action
- Avoid more than 2 consecutive sprays of the same chemical group
- Combine chemical control with biological methods

6. Role of Integrated Pest Management (IPM)
Chemical pesticides should be part of a broader IPM strategy, including:
- Regular orchard monitoring
- Use of pheromone traps
- Conservation of beneficial insects (ladybird beetles, lacewings)
- Neem-based products (Azadirachtin)

IPM reduces:
- Input costs
- Environmental damage
- Health risks to farmers

7. Regulatory and Environmental Considerations
- Several pesticides are restricted or banned if misused
- Excessive residues can lead to rejection in domestic and export markets
- Farmers should stay updated via state agriculture departments, Krishi Vigyan Kendras (KVKs), and authorized agri-input dealers

8. Conclusion
Pesticide use in Mosambi cultivation must be scientific, minimal, and need-based. A well-informed farmer who identifies pests correctly, applies the right chemical at the right time, and integrates non-chemical practices will achieve higher yields, better fruit quality, and long-term orchard health.
"""


async def fetch_weather_data(city: str) -> dict:
    """Fetch weather data from wttr.in API"""
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
    """List all available tools"""
    return [
        Tool(
            name="get_current_weather",
            description="Get current weather conditions for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name to get weather for"}
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="get_placeholder_posts",
            description="Fetch mock blog posts from JSONPlaceholder for testing",
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
                }
            }
        ),
        Tool(
            name="citrus_pests_diseases",
            description="If you need help with citrus pests and diseases related inputs for Indian farm conditions, this tool will help you with the proper inputs. Provides comprehensive information about Mosambi (Sweet Lemon) cultivation, pest management, disease control, and pesticide practices in India.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute the requested tool"""
    
    if name == "get_current_weather":
        city = arguments.get("city")
        if not city:
            return [TextContent(type="text", text="❌ Error: City name is required")]
        try:
            data = await fetch_weather_data(city)
            current = data["current_condition"][0]
            result = (
                f"🌍 Weather for {city}:\n"
                f"🌡️  Temperature: {current['temp_C']}°C\n"
                f"☁️  Condition: {current['weatherDesc'][0]['value']}\n"
                f"💧 Humidity: {current['humidity']}%"
            )
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error: {str(e)}")]

    elif name == "get_placeholder_posts":
        limit = arguments.get("limit", 5)
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get("https://jsonplaceholder.typicode.com/posts")
                response.raise_for_status()
                posts = response.json()[:limit]
                
                formatted = "\n\n".join([
                    f"📝 Post #{p['id']}: {p['title']}\n{p['body'][:100]}..." 
                    for p in posts
                ])
                return [TextContent(type="text", text=f"✅ Fetched {len(posts)} posts:\n\n{formatted}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error: {str(e)}")]

    elif name == "citrus_pests_diseases":
        """
        RAG Tool: Citrus Pests and Diseases Knowledge Base
        
        This tool returns the comprehensive citrus knowledge base.
        The LLM (agent) will use this information to answer the user's question about
        citrus farming, pest management, and pesticide practices in India.
        
        The key difference from other tools:
        - No parameters needed - just return the knowledge base
        - The agent's original message IS the question being asked
        - The LLM will use the knowledge base to synthesize an answer
        """
        
        # Return the knowledge base directly
        # The agent has the original user message in context
        # So it can match this knowledge base against the user's question
        result = f"""🌾 CITRUS FARMING KNOWLEDGE BASE - Indian Farm Conditions

Below is comprehensive information about citrus pest management, disease control, and pesticide practices for Mosambi (Sweet Lemon) cultivation in India:

{CITRUS_KNOWLEDGE_BASE}

---

This knowledge base covers:
✓ Major pests: Citrus Psylla, Leaf Miner, Aphids, Mealybugs, Red Spider Mites
✓ Diseases: Citrus Canker, Phytophthora (Root Rot), Powdery Mildew
✓ Pesticides and fungicides with dosages
✓ Application practices and timing
✓ Safety and pre-harvest intervals
✓ Integrated Pest Management (IPM)
✓ Resistance management strategies

Use this information to answer questions about citrus farming in Indian farm conditions.
"""
        return [TextContent(type="text", text=result)]

    return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]


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