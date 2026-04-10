from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import Tool
from services.llm import llm
from services.tools import tools

system_prompt = (
    "You are a healthcare assistant.\n"
    "You MUST use available tools when appropriate.\n"
    "Do NOT answer directly if a tool is relevant.\n\n"
    "Rules:\n"
    "- If user asks about doctor → use Doctor Suggestion tool\n"
    "- If user asks about hospital → use Hospital Finder tool\n"
    "- If user asks health advice → use Health Advice tool\n"
)

_llm_with_tools = llm.bind_tools(tools)

def _tool_map():
    return {t.name: t for t in tools}

class AgentWrapper:
    def invoke(self, inputs):
        from services.memory import get_memory

        session_id = inputs.get("session_id")
        messages = [SystemMessage(content=system_prompt)]

        if session_id:
            history = get_memory(session_id)
            for msg in history:
                if msg["sender"] == "client" and msg["message"] != inputs.get("input"):
                    messages.append(HumanMessage(content=msg["message"]))
                elif msg["sender"] == "bot":
                    messages.append(AIMessage(content=msg["message"]))

        messages.append(HumanMessage(content=inputs["input"]))

        response = _llm_with_tools.invoke(messages)

        # If the LLM called a tool, execute it and return the result
        if response.tool_calls:
            call = response.tool_calls[0]
            tool = _tool_map().get(call["name"])
            if tool:
                tool_input = list(call["args"].values())[0] if call["args"] else inputs["input"]
                result = tool.func(tool_input)
                print(f"\n[AGENT] Tool called: {call['name']} | Input: {tool_input}")
                return {"output": result}

        return {"output": response.content}

agent = AgentWrapper()
