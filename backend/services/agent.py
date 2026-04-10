from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from typing import TypedDict
from services.llm import llm
from services.tools import find_hospital, suggest_doctor, health_advice


class AgentState(TypedDict):
    input: str
    output: str


def agent_node(state: AgentState):
    user_input = state["input"]

    # Give the LLM context about available tools
    system_prompt = (
        "You are a healthcare assistant. "
        "You help users with symptoms, hospital searches, and doctor suggestions. "
        "Be concise and helpful."
    )

    response = llm.invoke([
        HumanMessage(content=f"{system_prompt}\n\nUser: {user_input}")
    ])

    return {"output": response.content}


graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.set_entry_point("agent")
graph.set_finish_point("agent")

app = graph.compile()
