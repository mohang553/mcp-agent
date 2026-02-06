#!/usr/bin/env python3
"""
🚀 Dynamic LangGraph ReAct Agent with MCP Tools
Uses LangGraph's built-in create_react_agent for automatic tool selection
No hardcoding - discovers and uses ALL tools from ALL MCP servers dynamically!
"""
import os
import asyncio
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool, StructuredTool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()


# ============================================================================
# MCP CLIENT & MANAGER
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
# MCP TOOL WRAPPER FOR LANGCHAIN
# ============================================================================

class MCPToolWrapper:
    """
    Wraps MCP tools as LangChain tools
    This allows LangGraph's create_react_agent to use them!
    """
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        self.tool_to_server: Dict[str, str] = {}
        
    async def discover_and_wrap_tools(self) -> List[StructuredTool]:
        """
        Discovers all tools from all MCP servers and wraps them as LangChain tools
        """
        print("\n🔍 Discovering tools from all MCP servers...")
        
        langchain_tools = []
        total_tools = 0
        
        for server_name, client in self.mcp_manager.clients.items():
            try:
                async with client.connect():
                    tools = await client.get_tools()
                    
                    print(f"   ✅ {server_name}: {len(tools)} tools")
                    
                    for tool_def in tools:
                        # Store mapping
                        self.tool_to_server[tool_def['name']] = server_name
                        
                        # Create LangChain tool
                        langchain_tool = self._create_langchain_tool(
                            server_name,
                            tool_def
                        )
                        langchain_tools.append(langchain_tool)
                        
                        print(f"      • {tool_def['name']}: {tool_def.get('description', 'No description')[:60]}...")
                        
                        total_tools += 1
                        
            except Exception as e:
                print(f"   ⚠️  {server_name}: Failed - {e}")
        
        print(f"\n🎯 Total tools wrapped: {total_tools} across {len(self.mcp_manager.clients)} servers")
        
        return langchain_tools
    
    def _create_langchain_tool(self, server_name: str, tool_def: Dict) -> StructuredTool:
        """
        Creates a LangChain StructuredTool from an MCP tool definition
        """
        tool_name = tool_def['name']
        tool_description = tool_def.get('description', f"Tool from {server_name}")
        tool_schema = tool_def.get('inputSchema', {})
        
        # Create async function that calls the MCP tool
        async def mcp_tool_function(**kwargs) -> str:
            """Dynamically generated function that calls MCP tool"""
            client = self.mcp_manager.clients[server_name]
            async with client.connect():
                result = await client.call_tool(tool_name, kwargs)
                return result
        
        # Extract parameter info from schema
        properties = tool_schema.get('properties', {})
        required = tool_schema.get('required', [])
        
        # Build args schema for LangChain
        args_schema = {}
        for param_name, param_info in properties.items():
            param_type = param_info.get('type', 'string')
            param_desc = param_info.get('description', '')
            
            # Map JSON schema types to Python types
            type_mapping = {
                'string': str,
                'integer': int,
                'number': float,
                'boolean': bool,
                'array': list,
                'object': dict
            }
            
            python_type = type_mapping.get(param_type, str)
            
            # Add to args schema
            args_schema[param_name] = (python_type, param_desc)
        
        # Create the LangChain tool
        return StructuredTool.from_function(
            coroutine=mcp_tool_function,
            name=tool_name,
            description=tool_description,
            # args_schema can be passed if needed for validation
        )


# ============================================================================
# LANGGRAPH REACT AGENT
# ============================================================================

class DynamicMCPAgent:
    """
    Dynamic agent that uses LangGraph's create_react_agent with MCP tools
    """
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        self.llm = None
        self.agent_executor = None
        self.tool_wrapper = MCPToolWrapper(mcp_manager)
        
    async def initialize(self):
        """Initialize LLM and discover tools"""
        
        # Initialize LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables!")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            google_api_key=api_key
        )
        print("🧠 LLM initialized: gemini-1.5-flash")
        
        # Discover and wrap all MCP tools
        langchain_tools = await self.tool_wrapper.discover_and_wrap_tools()
        
        if not langchain_tools:
            print("⚠️  WARNING: No tools found!")
            return
        
        # Create ReAct agent with all tools
        self.agent_executor = create_react_agent(self.llm, langchain_tools)
        
        print(f"\n✅ ReAct Agent created with {len(langchain_tools)} tools")
        print("🎯 Agent will automatically select the best tool for each query!")
        
    async def run(self, user_message: str) -> Dict[str, Any]:
        """Run the agent with a user message"""
        
        if not self.agent_executor:
            return {
                "response": "Agent not initialized",
                "error": "No tools available"
            }
        
        print(f"\n{'='*70}")
        print(f"💬 User Query: {user_message}")
        print(f"{'='*70}")
        
        try:
            # Run the ReAct agent
            inputs = {"messages": [HumanMessage(content=user_message)]}
            result = await self.agent_executor.ainvoke(inputs)
            
            # Extract final answer
            final_answer = result["messages"][-1].content
            
            # Extract intermediate steps (tool calls)
            intermediate_steps = []
            for msg in result["messages"][:-1]:
                if hasattr(msg, 'name') and msg.name:
                    intermediate_steps.append(f"Tool used: {msg.name}")
            
            print(f"\n✅ Agent completed")
            print(f"{'='*70}\n")
            
            return {
                "response": final_answer,
                "intermediate_steps": intermediate_steps
            }
            
        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "response": "Sorry, I encountered an error processing your request.",
                "error": error_msg
            }


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

mcp_manager: Optional[MCPManager] = None
dynamic_agent: Optional[DynamicMCPAgent] = None


class ChatRequest(BaseModel):
    """Simple chat request"""
    message: str


class ChatResponse(BaseModel):
    response: str
    intermediate_steps: Optional[List[str]] = None
    error: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    global mcp_manager, dynamic_agent
    
    print("\n" + "="*70)
    print("🚀 Dynamic LangGraph + MCP Agent")
    print("="*70)
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("\n❌ ERROR: GOOGLE_API_KEY not found!")
        print("   Set it in your .env file")
    else:
        # Initialize MCP manager
        mcp_manager = MCPManager()
        await mcp_manager.initialize_clients()
        
        if not mcp_manager.clients:
            print("\n⚠️  WARNING: No MCP servers configured!")
        else:
            # Initialize dynamic agent
            dynamic_agent = DynamicMCPAgent(mcp_manager)
            await dynamic_agent.initialize()
    
    print("\n" + "="*70)
    print("✅ Server Ready!")
    print("="*70)
    print("📡 URL: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("="*70 + "\n")
    
    yield
    
    print("\n👋 Shutting down...")


app = FastAPI(
    title="Dynamic LangGraph + MCP Agent API",
    description="Uses LangGraph's ReAct agent with automatically discovered MCP tools",
    version="4.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """API info"""
    if not dynamic_agent:
        return {
            "status": "error",
            "message": "Agent not initialized"
        }
    
    return {
        "name": "Dynamic LangGraph + MCP Agent API",
        "version": "4.0",
        "status": "online",
        "agent_type": "LangGraph ReAct Agent",
        "llm_model": "gemini-1.5-flash",
        "servers": list(mcp_manager.clients.keys()) if mcp_manager else [],
        "total_tools": len(dynamic_agent.tool_wrapper.tool_to_server) if dynamic_agent else 0,
        "features": [
            "🤖 LangGraph ReAct agent (built-in reasoning)",
            "🔍 Automatic tool discovery from MCP servers",
            "🧠 LLM-powered tool selection",
            "📝 Multi-step reasoning",
            "🔌 Multi-server support",
            "✨ Zero hardcoding - add tools and they work instantly!"
        ]
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat with the dynamic agent
    
    The agent will:
    1. Understand your query
    2. Decide which tool(s) to use
    3. Execute the tools
    4. Reason about the results
    5. Return a final answer
    
    Examples:
    - "What's the weather in Tokyo?"
    - "Tell me about organic pesticides"
    - "Show me 5 blog posts"
    - "Calculate 100 * 5 and tell me the result"
    
    The agent can use multiple tools in sequence if needed!
    """
    if not dynamic_agent:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized - check GOOGLE_API_KEY and config.json"
        )
    
    try:
        result = await dynamic_agent.run(request.message)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    """List all available tools"""
    if not dynamic_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    tools_by_server = {}
    for server_name, client in mcp_manager.clients.items():
        async with client.connect():
            tools = await client.get_tools()
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
        "status": "healthy" if dynamic_agent else "unhealthy",
        "agent_initialized": dynamic_agent is not None,
        "llm_initialized": dynamic_agent.llm is not None if dynamic_agent else False,
        "servers_configured": len(mcp_manager.clients) if mcp_manager else 0,
        "tools_loaded": len(dynamic_agent.tool_wrapper.tool_to_server) if dynamic_agent else 0
    }


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🚀 Starting Dynamic LangGraph + MCP Agent Server")
    print("="*70)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")