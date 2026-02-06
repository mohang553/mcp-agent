# 🌾 Intelligent LangGraph Agent with Agricultural Tool

## 🎯 What's New

### ✨ Features Added

1. **🤖 Intelligent LangGraph Agent** with **4 nodes**:
   - `analyze` - Detects intent and selects tool
   - `extract_args` - Extracts arguments from user query
   - `execute_tool` - Calls the MCP tool
   - `format_response` - Formats the final output

2. **🌾 New Tool: Pesticide & Seed Information**
   - Responds to agriculture queries
   - Provides farming information
   - Handles seed and pesticide questions

3. **🧠 Automatic Tool Routing**
   - No need to specify which tool to use
   - Agent intelligently selects based on your query
   - Extracts arguments automatically

## 📊 Agent Architecture

```
User Query: "What pesticides for tomatoes?"
     │
     ▼
┌────────────────┐
│ Node 1: analyze│  → Detects "pesticides" keyword
│                │  → Selects: get_pesticide_seed_info
└────────┬───────┘
         │
         ▼
┌────────────────┐
│Node 2: extract │  → Extracts: query="pesticides for tomatoes"
│     _args      │
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ Node 3: execute│  → Calls MCP server
│     _tool      │  → Gets agricultural info
└────────┬───────┘
         │
         ▼
┌────────────────┐
│Node 4: format  │  → Returns formatted response
│   _response    │
└────────┬───────┘
         │
         ▼
    Response to User
```

## 🚀 Quick Start

### Step 1: File Structure

Put these files in the same directory:

```
D:\projects\my_mcp_demo\
├── enhanced_mcp_server.py          # MCP server with 3 tools
├── intelligent_mcp_server.py       # FastAPI with LangGraph agent
├── config_agricultural.json        # Configuration
└── test_intelligent_agent.py       # Test script (optional)
```

### Step 2: Update Config

Edit `config_agricultural.json` with your Python path:

```json
{
  "mcpServers": {
    "agricultural-server": {
      "command": "D:\\projects\\env\\Scripts\\python.exe",
      "args": ["D:\\projects\\my_mcp_demo\\enhanced_mcp_server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

**Important**: 
- Use FULL paths
- Use double backslashes `\\` in Windows paths
- Update both `command` and `args` paths

### Step 3: Rename Config

```bash
# Rename to config.json so the server finds it
ren config_agricultural.json config.json
```

### Step 4: Install Dependencies

```bash
pip install fastapi uvicorn mcp httpx pydantic langgraph langchain-core
```

### Step 5: Start the Server

```bash
python intelligent_mcp_server.py
```

You should see:
```
============================================================
🚀 MCP Intelligent Agent API Server
============================================================
📡 Starting on: http://localhost:8000
📚 API Docs at: http://localhost:8000/docs
🤖 Agent Type: LangGraph with 4 nodes
============================================================

🚀 Starting MCP Agent API with Intelligent LangGraph Agent...
✅ Found config file: D:\projects\my_mcp_demo\config.json
✅ Initialized client for: agricultural-server
✅ MCP Manager ready
```

## 🧪 Testing the Agent

### Test 1: Agricultural Query

```bash
curl -X POST "http://localhost:8000/chat-agent" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Tell me about pesticides for wheat farming\"}"
```

**Expected Response:**
```json
{
  "response": "🌾 Welcome to Pesticide and Seed Information Service! 🌱\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nQuery: pesticides for wheat farming\n\nI will fetch comprehensive information about seeds and pesticides for you!...",
  "server_name": "agricultural-server"
}
```

**What happened:**
1. ✅ analyze_node detected "pesticides" keyword
2. ✅ Selected tool: `get_pesticide_seed_info`
3. ✅ extract_args extracted query: "pesticides for wheat farming"
4. ✅ execute_tool called the MCP server
5. ✅ format_response returned the result

### Test 2: Weather Query

```bash
curl -X POST "http://localhost:8000/chat-agent" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What's the weather in Paris?\"}"
```

**What happens:**
1. ✅ analyze_node detects "weather" keyword
2. ✅ Selected tool: `get_current_weather`
3. ✅ extract_args extracts city: "Paris"
4. ✅ Fetches real weather data

### Test 3: Blog Posts Query

```bash
curl -X POST "http://localhost:8000/chat-agent" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Show me 5 blog posts\"}"
```

**What happens:**
1. ✅ analyze_node detects "blog posts" keywords
2. ✅ Selected tool: `get_placeholder_posts`
3. ✅ extract_args extracts limit: 5
4. ✅ Fetches 5 posts

## 🎨 Interactive Testing

Open your browser: **http://localhost:8000/docs**

You'll see Swagger UI with interactive API documentation!

### Try these queries:

1. **"What are the best seeds for corn?"**
   - Should route to pesticide_seed_info
   - Query extracted: "best seeds for corn"

2. **"Weather forecast for Tokyo"**
   - Should route to get_current_weather
   - City extracted: "Tokyo"

3. **"Give me 3 articles"**
   - Should route to get_placeholder_posts
   - Limit extracted: 3

4. **"How to deal with pests in my garden?"**
   - Should route to pesticide_seed_info
   - Query: "deal with pests in my garden"

## 📊 Available Tools

The agent automatically chooses from:

| Tool | Triggers | Arguments |
|------|----------|-----------|
| `get_pesticide_seed_info` | pesticide, seed, farm, crop, agriculture, plant | query (string) |
| `get_current_weather` | weather, temperature, climate, forecast | city (string) |
| `get_placeholder_posts` | post, blog, article | limit (number) |

## 🔧 How Tool Routing Works

### Keyword Detection

```python
# In analyze_node:

weather_keywords = ["weather", "temperature", "climate", "forecast"]
→ Selects: get_current_weather

agriculture_keywords = ["pesticide", "pest", "seed", "farm", "crop", "agriculture", "plant"]
→ Selects: get_pesticide_seed_info

blog_keywords = ["post", "blog", "article"]
→ Selects: get_placeholder_posts
```

### Argument Extraction

```python
# For weather:
"Weather in Paris" → city = "Paris"

# For agriculture:
"Tell me about organic pesticides" → query = "organic pesticides"

# For posts:
"Show me 10 posts" → limit = 10
```

## 🎯 Node Breakdown

### Node 1: analyze (Decision Maker)
```python
Input: "What pesticides for tomatoes?"
Process:
  - Converts to lowercase
  - Checks for keywords
  - Finds "pesticides" → agriculture query
Output: current_tool = "get_pesticide_seed_info"
        reasoning = "Agriculture query detected"
```

### Node 2: extract_args (Argument Extractor)
```python
Input: current_tool = "get_pesticide_seed_info"
       user_message = "What pesticides for tomatoes?"
Process:
  - Extracts query from message
  - Cleans up text
Output: tool_arguments = {"query": "pesticides for tomatoes"}
```

### Node 3: execute_tool (Executor)
```python
Input: current_tool = "get_pesticide_seed_info"
       tool_arguments = {"query": "pesticides for tomatoes"}
Process:
  - Connects to MCP server
  - Calls: get_pesticide_seed_info(query="pesticides for tomatoes")
  - Waits for response
Output: final_response = "🌾 Welcome to Pesticide and Seed Information..."
```

### Node 4: format_response (Formatter)
```python
Input: final_response = "🌾 Welcome to..."
Process:
  - Optionally adds metadata
  - Could add debug info
  - Could translate or summarize
Output: formatted final_response
```

## 🌟 Advanced Usage

### Custom Queries

The agent is smart enough to handle variations:

```bash
# All of these route to pesticide_seed_info:
"best pesticides"
"organic farming methods"
"what seeds to plant in spring"
"crop rotation for wheat"
"pest control solutions"
"fertilizer recommendations"
```

### Multiple Tools in Conversation

Currently each query is independent, but you can chain them:

```bash
# Query 1
curl -X POST http://localhost:8000/chat-agent \
  -d '{"message": "Weather in Mumbai"}'
  
# Query 2
curl -X POST http://localhost:8000/chat-agent \
  -d '{"message": "Best seeds for Mumbai climate"}'
```

## 🔮 Future Enhancements

### Coming Soon:
1. **LLM Integration** - Use GPT/Claude for better understanding
2. **Context Memory** - Remember previous questions
3. **Multi-tool Queries** - "Weather in Paris and best crops for that climate"
4. **Real Database** - Connect pesticide_seed_info to actual database
5. **User Preferences** - Remember user's location/interests

## 🐛 Troubleshooting

### Issue: "Server not found"
```
Solution: Check config.json is in the same directory as intelligent_mcp_server.py
```

### Issue: "No tools loaded"
```
Check:
1. enhanced_mcp_server.py exists
2. Paths in config.json are correct
3. Python executable is correct
```

### Issue: "Wrong tool selected"
```
The routing uses keyword matching. Add more keywords in analyze_node:

agriculture_keywords = ["pesticide", "pest", "seed", "farm", ...]
```

### Issue: "Arguments not extracted"
```
Improve extraction logic in extract_arguments_node:

def _extract_city(self, text: str) -> str:
    # Add more patterns
    ...
```

## 📝 Example Sessions

### Session 1: Farming Advice
```
User: "What pesticides should I use for organic tomato farming?"

Agent Flow:
1. analyze: Detects "pesticides" and "farming" → pesticide_seed_info
2. extract_args: query = "pesticides organic tomato farming"
3. execute: Calls MCP tool
4. format: Returns agricultural information

Response: "🌾 Welcome to Pesticide and Seed Information Service!..."
```

### Session 2: Weather Check
```
User: "Is it raining in London?"

Agent Flow:
1. analyze: Detects "raining" (weather context) → get_current_weather
2. extract_args: city = "London"
3. execute: Calls weather API
4. format: Returns weather data

Response: "🌤️ Current Weather in London: 12°C, Cloudy, 78% humidity"
```

### Session 3: Content Discovery
```
User: "Find me 7 interesting articles"

Agent Flow:
1. analyze: Detects "articles" → get_placeholder_posts
2. extract_args: limit = 7
3. execute: Fetches posts
4. format: Returns posts

Response: "📚 Fetched 7 blog posts: [list of posts]"
```

## 🎓 Learning Resources

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **MCP Docs**: https://modelcontextprotocol.io
- **FastAPI Docs**: https://fastapi.tiangolo.com

## 🎉 Summary

You now have:
- ✅ **4-node LangGraph agent** with intelligent routing
- ✅ **3 tools**: Weather, Posts, Agriculture
- ✅ **Automatic tool selection** based on query
- ✅ **Argument extraction** from natural language
- ✅ **REST API** for easy integration

Just send a message, and the agent figures out what to do! 🚀