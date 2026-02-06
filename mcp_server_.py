#!/usr/bin/env python3
"""
🚀 FULLY DYNAMIC LLM-POWERED MCP AGENT
No hardcoded keywords - LLM decides everything!
Automatically adapts to ANY tools you add to your MCP servers.
"""
import asyncio
import json
import sys
import os
import re
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ============================================================================
# MCP CLIENT & MANAGER (Same as before)
# ============================================================================

class MCPClient:
    """Client to interact with MCP servers"""
    
    def __init__(self, server_name: str, server_config: Dict[str, Any]):
        self.server_name = server_name
        self.server_config = server_config
        self.session: Optional[ClientSession] = None
        self.available_tools: List[Dict] = []
        
    @asynccontextmanager
    async def connect(self):
        """Connect to the MCP server"""
        server_params = StdioServerParameters(
            command=self.server_config["command"],
            args=self.server_config.get("args", []),
            env={**os.environ, **self.server_config.get("env", {})}
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                await session.initialize()
                
                tools_list = await session.list_tools()
                self.available_tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in tools_list.tools
                ]
                
                yield self
    
    async def get_tools(self) -> List[Dict]:
        return self.available_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        result = await self.session.call_tool(tool_name, arguments)
        
        if result.content:
            return "\n".join([
                item.text for item in result.content 
                if hasattr(item, 'text')
            ])
        return "No response from tool"


class MCPManager:
    """Manages multiple MCP server connections"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.clients: Dict[str, MCPClient] = {}
        
    def find_config_file(self) -> Optional[Path]:
        script_dir = Path(__file__).parent.absolute()
        search_paths = [
            script_dir / self.config_path,
            script_dir.parent / self.config_path,
            Path.cwd() / self.config_path,
        ]
        
        for path in search_paths:
            if path.exists() and path.is_file():
                return path
        return None
        
    def load_config(self) -> Dict[str, Any]:
        try:
            config_file = self.find_config_file()
            
            if not config_file:
                print(f"❌ Config file '{self.config_path}' not found!")
                return {}
            
            print(f"✅ Found config file: {config_file}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("mcpServers", {})
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}
    
    async def initialize_clients(self):
        servers_config = self.load_config()
        
        if not servers_config:
            print("⚠️  No MCP servers found in config")
            return
        
        print(f"\n📡 Initializing {len(servers_config)} MCP servers...")
        for server_name, server_config in servers_config.items():
            self.clients[server_name] = MCPClient(server_name, server_config)
            print(f"   ✅ {server_name}")


# ============================================================================
# LLM-POWERED DYNAMIC AGENT
# ============================================================================

class LLMPoweredMCPAgent:
    """
    🧠 Intelligent agent powered by LLM
    

    - LLM reads tool descriptions
    - LLM selects the best tool
    - LLM extracts arguments
    - Works with ANY tools you add
    """
    
    def __init__(self, mcp_manager: MCPManager, llm_api_key: str = None):
        self.mcp_manager = mcp_manager
        self.all_tools: Dict[str, List[Dict]] = {}
        self.tool_to_server: Dict[str, str] = {}
        
        # Initialize LLM
        api_key = llm_api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found! Set it in .env or pass it to constructor")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0,
            google_api_key=api_key
        )
        
        print("🧠 LLM initialized: gemini-1.5-flash")
        
    async def initialize(self):
        """Discover all tools from all MCP servers"""
        print("\n🔍 Discovering tools from all MCP servers...")
        
        total_tools = 0
        for server_name, client in self.mcp_manager.clients.items():
            try:
                async with client.connect():
                    tools = await client.get_tools()
                    self.all_tools[server_name] = tools
                    
                    for tool in tools:
                        self.tool_to_server[tool['name']] = server_name
                    
                    print(f"   ✅ {server_name}: {len(tools)} tools")
                    for tool in tools:
                        print(f"      • {tool['name']}: {tool.get('description', 'No description')[:60]}...")
                    
                    total_tools += len(tools)
            except Exception as e:
                print(f"   ⚠️  {server_name}: Failed - {e}")
        
        print(f"\n🎯 Total tools available: {total_tools} across {len(self.all_tools)} servers")
        
        if total_tools == 0:
            print("\n⚠️  WARNING: No tools loaded!")
        
    def _format_tools_for_llm(self) -> str:
        """Format all tools as a clear list for the LLM"""
        tools_text = []
        
        for server_name, tools in self.all_tools.items():
            for tool in tools:
                schema = tool.get('inputSchema', {})
                properties = schema.get('properties', {})
                
                # Format parameters
                params = []
                for param_name, param_info in properties.items():
                    param_type = param_info.get('type', 'any')
                    param_desc = param_info.get('description', '')
                    params.append(f"  - {param_name} ({param_type}): {param_desc}")
                
                params_text = "\n".join(params) if params else "  - No parameters"
                
                tool_text = f"""
Tool: {tool['name']}
Server: {server_name}
Description: {tool.get('description', 'No description')}
Parameters:
{params_text}
"""
                tools_text.append(tool_text.strip())
        
        return "\n\n".join(tools_text)
    
    async def select_tool(self, user_message: str) -> Dict[str, Any]:
        """
        Use LLM to select the best tool for the user's query
        Returns: {"server": "...", "tool": "...", "reasoning": "..."}
        """
        tools_list = self._format_tools_for_llm()
        
        prompt = f"""You are an intelligent tool selection assistant. Given a user query and a list of available tools, select the BEST tool to answer the query.

AVAILABLE TOOLS:
{tools_list}

USER QUERY: {user_message}

Analyze the query and select the most appropriate tool. Respond ONLY with valid JSON in this EXACT format:
{{
  "server": "server-name",
  "tool": "tool-name",
  "reasoning": "brief explanation of why this tool was selected"
}}

Important:
- Choose the tool whose description best matches the user's intent
- Use EXACT tool and server names from the list above
- If no tool is perfect, choose the closest match
- Be concise in reasoning (1 sentence max)
"""
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result_text = response.content.strip()
            
            # Extract JSON from markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            print(f"\n🎯 LLM Selected: {result['server']}.{result['tool']}")
            print(f"   Reasoning: {result['reasoning']}")
            
            return result
        except Exception as e:
            print(f"❌ Error in tool selection: {e}")
            # Fallback to first available tool
            first_server = list(self.all_tools.keys())[0]
            first_tool = self.all_tools[first_server][0]['name']
            return {
                "server": first_server,
                "tool": first_tool,
                "reasoning": f"Fallback due to error: {str(e)}"
            }
    
    async def extract_arguments(self, user_message: str, tool_name: str, server_name: str) -> Dict[str, Any]:
        """
        Use LLM to extract arguments from user message based on tool schema
        """
        # Get tool schema
        tool_schema = None
        for tool in self.all_tools.get(server_name, []):
            if tool['name'] == tool_name:
                tool_schema = tool.get('inputSchema', {})
                break
        
        if not tool_schema or not tool_schema.get('properties'):
            return {}
        
        properties = tool_schema.get('properties', {})
        
        # Format schema for LLM
        schema_text = []
        for param_name, param_info in properties.items():
            param_type = param_info.get('type', 'any')
            param_desc = param_info.get('description', '')
            default = param_info.get('default', 'N/A')
            schema_text.append(f"  - {param_name} ({param_type}): {param_desc} [default: {default}]")
        
        schema_str = "\n".join(schema_text)
        
        prompt = f"""You are an argument extraction assistant. Extract the required arguments from the user's message.

TOOL: {tool_name}
PARAMETERS NEEDED:
{schema_str}

USER MESSAGE: {user_message}

Extract the arguments from the user's message. Respond ONLY with valid JSON mapping parameter names to their values.

Examples:
- If user says "weather in Paris" and tool needs "city", respond: {{"city": "Paris"}}
- If user says "show me 5 posts" and tool needs "limit", respond: {{"limit": 5}}
- If user says "tell me about pesticides" and tool needs "query", respond: {{"query": "pesticides"}}

Important:
- Use EXACT parameter names from the schema
- Match the expected type (string, integer, etc.)
- If a parameter isn't mentioned, use its default value or omit it
- Respond with ONLY the JSON object, nothing else

JSON:
"""
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result_text = response.content.strip()
            
            # Extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            arguments = json.loads(result_text)
            
            print(f"📋 LLM Extracted Arguments: {arguments}")
            
            return arguments
        except Exception as e:
            print(f"⚠️  Error extracting arguments: {e}")
            # Try basic extraction as fallback
            return self._basic_argument_extraction(user_message, properties)
    
    def _basic_argument_extraction(self, message: str, properties: Dict) -> Dict[str, Any]:
        """Fallback argument extraction without LLM"""
        arguments = {}
        
        for param_name, param_info in properties.items():
            param_type = param_info.get('type')
            
            if param_type == 'string':
                if 'city' in param_name.lower():
                    words = message.split()
                    for i, word in enumerate(words):
                        if word.lower() in ["in", "for", "at"] and i + 1 < len(words):
                            arguments[param_name] = words[i + 1].strip("?.,!").title()
                            break
                    if param_name not in arguments:
                        arguments[param_name] = "London"
                elif 'query' in param_name.lower():
                    arguments[param_name] = message
                else:
                    arguments[param_name] = message
            
            elif param_type == 'integer':
                numbers = re.findall(r'\b\d+\b', message)
                if numbers:
                    arguments[param_name] = int(numbers[0])
                elif 'default' in param_info:
                    arguments[param_name] = param_info['default']
        
        return arguments
    
    async def execute_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute the tool on the MCP server"""
        print(f"⚡ Executing: {server_name}.{tool_name}({arguments})")
        
        try:
            client = self.mcp_manager.clients[server_name]
            async with client.connect():
                result = await client.call_tool(tool_name, arguments)
                print(f"✅ Tool executed successfully")
                return result
        except Exception as e:
            error_msg = f"❌ Error executing tool: {str(e)}"
            print(error_msg)
            return error_msg
    
    async def run(self, user_message: str) -> Dict[str, Any]:
        """
        Main entry point - processes a user query end-to-end
        """
        print(f"\n{'='*70}")
        print(f"💬 User Query: {user_message}")
        print(f"{'='*70}")
        
        # Step 1: LLM selects the tool
        selection = await self.select_tool(user_message)
        server_name = selection['server']
        tool_name = selection['tool']
        reasoning = selection['reasoning']
        
        # Step 2: LLM extracts arguments
        arguments = await self.extract_arguments(user_message, tool_name, server_name)
        
        # Step 3: Execute the tool
        result = await self.execute_tool(server_name, tool_name, arguments)
        
        print(f"{'='*70}\n")
        
        return {
            "response": result,
            "server_used": server_name,
            "tool_used": tool_name,
            "arguments_used": arguments,
            "reasoning": reasoning
        }


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

mcp_manager: Optional[MCPManager] = None
llm_agent: Optional[LLMPoweredMCPAgent] = None


class ChatRequest(BaseModel):
    """Simple chat request"""
    message: str


class ChatResponse(BaseModel):
    response: str
    server_used: Optional[str] = None
    tool_used: Optional[str] = None
    arguments_used: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    global mcp_manager, llm_agent
    
    print("\n" + "="*70)
    print("🚀 LLM-Powered Dynamic MCP Agent")
    print("="*70)
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("\n❌ ERROR: GOOGLE_API_KEY not found!")
        print("   Please set it in your .env file or environment variables")
        print("   Example: GOOGLE_API_KEY=your_key_here")
    else:
        # Initialize manager
        mcp_manager = MCPManager()
        await mcp_manager.initialize_clients()
        
        if not mcp_manager.clients:
            print("\n⚠️  WARNING: No servers configured!")
        else:
            # Initialize LLM agent
            llm_agent = LLMPoweredMCPAgent(mcp_manager)
            await llm_agent.initialize()
    
    print("\n" + "="*70)
    print("✅ Server Ready!")
    print("="*70)
    print("📡 URL: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("="*70 + "\n")
    
    yield
    
    print("\n👋 Shutting down...")


app = FastAPI(
    title="LLM-Powered Dynamic MCP Agent API",
    description="Intelligent agent that uses LLM to understand and route to ANY tools",
    version="3.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API info"""
    if not llm_agent:
        return {
            "status": "error",
            "message": "Agent not initialized - check GOOGLE_API_KEY and config.json"
        }
    
    return {
        "name": "LLM-Powered Dynamic MCP Agent API",
        "version": "3.0",
        "status": "online",
        "llm_model": "gemini-2.0-flash-exp",
        "servers": list(mcp_manager.clients.keys()),
        "total_tools": sum(len(tools) for tools in llm_agent.all_tools.values()),
        "features": [
            "🧠 LLM-powered tool selection (no hardcoded keywords!)",
            "🔍 Automatic tool discovery",
            "📝 Intelligent argument extraction",
            "🔌 Multi-server support",
            "✨ Works with ANY tools you add - zero code changes!"
        ]
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message - LLM figures out which tool to use!
    
    Examples:
    - "What's the weather in Tokyo?"
    - "Tell me about organic farming"
    - "Show me 5 blog posts"
    - "Calculate 365 - 100" (if you have a calculator tool)
    - "What's today's date?" (if you have a date tool)
    
    The LLM will:
    1. Read all available tool descriptions
    2. Select the best tool for your query
    3. Extract the needed arguments
    4. Execute the tool
    5. Return the result
    """
    if not llm_agent:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized - check GOOGLE_API_KEY and config.json"
        )
    
    try:
        result = await llm_agent.run(request.message)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    """List all available tools"""
    if not llm_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    tools_by_server = {}
    for server_name, tools in llm_agent.all_tools.items():
        tools_by_server[server_name] = [
            {
                "name": t['name'],
                "description": t.get('description', ''),
                "parameters": list(t.get('inputSchema', {}).get('properties', {}).keys())
            }
            for t in tools
        ]
    
    return {
        "servers": len(tools_by_server),
        "total_tools": sum(len(t) for t in tools_by_server.values()),
        "tools": tools_by_server
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy" if llm_agent else "unhealthy",
        "llm_initialized": llm_agent is not None,
        "servers_configured": len(mcp_manager.clients) if mcp_manager else 0,
        "tools_loaded": sum(len(t) for t in llm_agent.all_tools.values()) if llm_agent else 0
    }


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🚀 Starting LLM-Powered Dynamic MCP Agent Server")
    print("="*70)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")