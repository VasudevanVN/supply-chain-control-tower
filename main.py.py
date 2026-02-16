

from typing import Annotated, TypedDict, Union
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import os
from dotenv import load_dotenv

# This command looks for the .env file in the same folder and loads the keys
load_dotenv()

# Now you can use them without typing the actual secret in your code
groq_key = os.getenv("GROQ_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

class ControlTowerState(TypedDict):
    # 'add_messages' allows agents to append their findings to the history
    messages: Annotated[list[BaseMessage], add_messages]
    # Tracks which SKU or risk is currently being analyzed
    current_risk_level: str
    # Stores the final email draft before approval
    draft_email: str

import sqlite3

def setup_mock_db():
    conn = sqlite3.connect("supply_chain.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            sku TEXT,
            stock_level INTEGER,
            reorder_point INTEGER,
            warehouse_location TEXT
        )
    """)
    # Add a mock stockout scenario
    cursor.execute("INSERT OR REPLACE INTO inventory VALUES (1, 'CHIP-X1', 50, 100, 'Singapore')")
    conn.commit()
    conn.close()

setup_mock_db()

from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit


# Connect to the database we created in Step 1
db = SQLDatabase.from_uri("sqlite:///supply_chain.db")

# Setup the toolkit which gives the agent tools to:
# 1. List tables, 2. Check schema, 3. Execute queries, 4. Check for errors
toolkit = SQLDatabaseToolkit(db=db, llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key))
tools = toolkit.get_tools()


from langchain_core.messages import SystemMessage
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key)
def analyst_node(state: ControlTowerState):
    messages = state["messages"]

    llm_with_tools = llm.bind_tools(tools)
    # System prompt tells the agent its specific role and constraints
    system_prompt = SystemMessage(content=(
        "You are a SQL Expert. When using tools, ensure your JSON arguments "
        "are perfectly formatted. Do not include extra text outside the tool call. "
        "If you see the 'inventory' table, use 'sql_db_schema' with 'table_names': 'inventory' "
        "to see the columns before writing a query."
    ))

    response = llm_with_tools.invoke([system_prompt] + messages)
    return {"messages": [response]}

from langchain_community.tools.tavily_search import TavilySearchResults
import os

# You will need a TAVILY_API_KEY from tavily.com
os.environ["TAVILY_API_KEY"] = tavily_key

# This tool will fetch up to 3 high-quality search results
search_tool = TavilySearchResults(k=3)

def sourcing_node(state: ControlTowerState):
    messages = state["messages"]

    system_prompt = SystemMessage(content=(
        "You are the Sourcing Intelligence Agent. Your goal is to find external "
        "disruptions (weather, port strikes, or geopolitical issues) that could "
        "affect the locations and SKUs mentioned by the Analyst. Use the search tool "
        "to find the latest 2026 news. Be specific about the impact duration."
    ))

    # Bind the search tool to the LLM
    llm_with_search = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key).bind_tools([search_tool])

    response = llm_with_search.invoke([system_prompt] + messages)
    return {"messages": [response]}

from langchain_core.messages import HumanMessage

def negotiator_node(state: ControlTowerState):
    messages = state["messages"]

    system_prompt = SystemMessage(content=(
        "You are the Procurement Negotiator Agent. Based on the Analyst's stockout "
        "report and the Sourcing Agent's disruption discovery, draft a professional "
        "email to our backup supplier. Propose an expedited shipment and ask for a "
        "quote. Your goal is to solve the stockout before it affects the customer."
    ))

    # The Negotiator synthesizes everything in the 'messages' history
    response = ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_key).invoke([system_prompt] + messages)
    return {"messages": [response], "draft_email": response.content}

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode


all_tools = tools + [search_tool] # 'tools' is from Analyst, 'search_tool' from Sourcing
tool_node = ToolNode(all_tools)
# 1. Initialize the Graph with our State schema
workflow = StateGraph(ControlTowerState)

# 2. Add our Nodes
workflow.add_node("analyst", analyst_node)
workflow.add_node("sourcing", sourcing_node)
workflow.add_node("negotiator", negotiator_node)
workflow.add_node("tools", tool_node)
# Define the flow with conditional edges
def should_continue(state: ControlTowerState):
    messages = state["messages"]
    last_message = messages[-1]
    # If the LLM made a tool call, route to the 'tools' node
    if last_message.tool_calls:
        return "tools"
    # Otherwise, finish or move to next agent
    return "continue"

# 1. Analyst -> Tools (if needed) -> Sourcing
workflow.add_edge(START, "analyst")
workflow.add_conditional_edges("analyst", should_continue, {"tools": "tools", "continue": "sourcing"})

# 2. Sourcing -> Tools (if needed) -> Negotiator
workflow.add_conditional_edges("sourcing", should_continue, {"tools": "tools", "continue": "negotiator"})

# 3. Tools back to the agent that called them
# Note: This requires a bit more routing logic if you have multiple agents calling tools,
# but for now, we can route 'tools' back to the previous agent.
workflow.add_edge("tools", "analyst") # Or a more complex router

workflow.add_edge("negotiator", END)
app = workflow.compile()

inputs = {
    "messages": [HumanMessage(content="Run a risk assessment for our high-priority SKUs.")]
}

for output in app.stream(inputs):
    for key, value in output.items():
        print(f"\n--- Output from Node: {key} ---")
        print(value)

