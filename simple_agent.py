
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from tavily import TavilyClient

load_dotenv()

# --- Initialize AI and Search ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# --- Define Tools ---

@tool
def web_search(query: str) -> str:
    """Search the web for current information, news, and facts."""
    results = tavily_client.search(query, max_results=3)
    formatted = [f"Title: {r['title']}\nContent: {r['content']}\n" for r in results['results']]
    return "\n---\n".join(formatted)

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression. Example: '365 - 100'"""
    try:
        # Simple eval for demonstration; consider safe alternatives for production
        return f"Result: {eval(expression)}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_agricultural_info(query: str = "") -> str:
    """
    Provides welcome and introductory information about pesticides and seeds.
    Use this for general agriculture domain questions.
    """
    return ("Hello, welcome to the agricultural information domain! "
            "I will help you to get information regarding pesticides and seeds.")

tools = [web_search, calculator, get_agricultural_info]
agent_executor = create_react_agent(llm, tools)

# --- FastAPI Setup ---

app = FastAPI(title="Dynamic LangGraph Agent API")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    intermediate_steps: Optional[List[str]] = None

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to interact with the LangGraph agent.
    The agent automatically decides which tool to use.
    """
    try:
        # Run the agent with the user's message
        inputs = {"messages": [HumanMessage(content=request.message)]}
        result = await agent_executor.ainvoke(inputs)
        
        # Extract the last message content (the agent's final answer)
        final_answer = result["messages"][-1].content
        
        return ChatResponse(response=final_answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

# --- Run the Server ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)