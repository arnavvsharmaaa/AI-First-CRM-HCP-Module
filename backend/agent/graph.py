import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from agent.state import AgentState
from agent.tools.log_interaction import log_interaction
from agent.tools.edit_interaction import edit_interaction
from agent.tools.suggest_followups import suggest_followups
from agent.tools.search_hcp import search_hcp
from agent.tools.get_interaction import get_interaction

load_dotenv()

# ── All 5 tools ──────────────────────────────────────────────────────────────
tools = [
    log_interaction,
    edit_interaction,
    suggest_followups,
    search_hcp,
    get_interaction,
]

# ── LLM — primary: llama-3.3-70b-versatile (best tool-use quality on Groq) ──
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)
llm_with_tools = llm.bind_tools(tools)


# ── Nodes ─────────────────────────────────────────────────────────────────────
async def router_node(state: AgentState):
    """
    The entry node. Reads the conversation so far and asks the LLM to either:
    - Call one of the 5 tools (returns tool_calls), or
    - Respond directly with a plain text answer (no tool_calls → END).
    """
    messages = state["messages"]

    print(f"--- router_node called ({len(messages)} messages in state) ---")

    # Build the system prompt — inject the current interaction_id if known
    sys_content = (
        "You are a helpful AI assistant for a pharmaceutical CRM system.\n"
        "You help field reps log HCP interactions, search for doctors, "
        "retrieve past interactions, and suggest follow-up actions.\n\n"
        "Available tools:\n"
        "  • log_interaction   — Parse a natural language description and log a NEW interaction\n"
        "  • edit_interaction  — Update specific fields of the CURRENT interaction\n"
        "  • suggest_followups — Generate 3-5 follow-up action suggestions\n"
        "  • search_hcp        — Find an HCP by name in the database\n"
        "  • get_interaction   — Load a PAST interaction by HCP name or date\n\n"
        "Always call the most appropriate tool. "
        "If the user is describing a new interaction, call log_interaction. "
        "If the user wants to change a field, call edit_interaction. "
        "Never respond with raw JSON — always use a tool."
    )

    if state.get("interaction_id"):
        sys_content += (
            f"\n\nThe current interaction ID is: '{state['interaction_id']}'. "
            "Pass this as interaction_id to edit_interaction if the user wants to edit."
        )

    print("Invoking LLM to decide next action...")
    response = await llm_with_tools.ainvoke(
        [SystemMessage(content=sys_content)] + messages
    )
    print(f"LLM response — tool_calls: {getattr(response, 'tool_calls', None)}")

    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """
    Conditional edge: route to 'tools' if the LLM issued tool calls, else END.
    """
    last_message = state["messages"][-1]
    print("--- should_continue called ---")

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print(f"Routing to tools: {[tc['name'] for tc in last_message.tool_calls]}")
        return "tools"

    print("No tool calls — routing to END.")
    return END


# ── Graph assembly ─────────────────────────────────────────────────────────────
builder = StateGraph(AgentState)

builder.add_node("router", router_node)
builder.add_node("tools", ToolNode(tools))

builder.set_entry_point("router")
builder.add_conditional_edges(
    "router",
    should_continue,
    {"tools": "tools", END: END},
)
builder.add_edge("tools", "router")

graph = builder.compile()
