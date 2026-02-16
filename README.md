Multi-Agent Supply Chain Control Tower

An autonomous, agentic AI system designed to detect, analyze, and mitigate supply chain risks in real-time.
This project moves beyond static dashboards by using a Perception–Reasoning–Action loop to solve inventory disruptions.

Architecture

The system is built as a Stateful Directed Cyclic Graph using LangGraph. It coordinates three specialized agents that share a global memory (State) to solve complex logistics problems:
Inventory Analyst Agent (Internal Brain):

Role: Monitors internal health.

Capability: Autonomously discovers SQL database schemas and executes complex queries to identify stockouts or items below reorder points.

Sourcing Intelligence Agent (External Eye):

Role: Contextualizes internal alerts with global events.

Capability: Uses real-time web search to identify "Black Swan" events (port strikes, weather disruptions, or geopolitical shifts) affecting specific warehouse locations identified by the Analyst.

Procurement Negotiator Agent (Action Taker):

Role: Closes the loop.

Capability: Synthesizes internal data and external risk intelligence to draft professional procurement strategies and expedited shipment requests to backup suppliers.

Tech Stack
Orchestration:  (for managing complex, cyclic agent workflows).

LLM "Brain":  via Groq (chosen for high-speed reasoning and superior tool-calling capabilities).

Internal Data: SQLite (structured inventory management).

Search Engine: Tavily API (optimized search for LLM agents).

Framework: LangChain (for tool-binding and prompt management).

Setup & Installation
1. Prerequisites
Python 3.10+

A Groq API Key (Free tier available at )

A Tavily API Key (Free tier available at )

2. Installation
Clone the repository and install the dependencies:

3. Environment Variables
To run the project, you need to set your API keys. In your terminal (or .env file):

Note: If running in Google Colab, use the "Secrets" (key icon) tab to store these as GROQ_API_KEY and TAVILY_API_KEY.

4. Running the System
Execute the main script to trigger the autonomous risk assessment:

Sample Output
The system follows a transparent reasoning chain:

Analyst: "Identified stockout for SKU CHIP-X1 in Singapore (Stock: 50, Threshold: 100)."

Sourcing: "Found 7.1-day average dwell time at Singapore Port due to network congestion and monsoon weather."

Negotiator: "Drafting urgent email to backup supplier for 50 units of CHIP-X1 via expedited air freight."
