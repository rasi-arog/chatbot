import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from services.llm import llm
from services.tools import tools, set_location

system_prompt = """You are a healthcare assistant. You MUST use the available tools for all health-related queries.

Tool usage rules:
- User asks about symptoms or health advice → use health_advice tool
- User asks which doctor or specialist to see → use doctor_suggestion tool
- User asks for nearby hospital or clinic → use hospital_finder tool
- Emergency (chest pain, can't breathe, unconscious, heart attack, stroke) → respond immediately with type "alert"

If no tool applies, respond in this EXACT JSON format:
{
  "type": "text",
  "message": "<your response here>",
  "data": {}
}

Always add a disclaimer that you do not provide medical diagnosis.
Never answer health questions directly without using a tool."""

_llm_with_tools = llm.bind_tools(tools)

def _tool_map():
    return {t.name: t for t in tools}

class AgentWrapper:
    def invoke(self, inputs: dict) -> dict:
        from services.memory import get_memory

        session_id = inputs.get("session_id")
        lat = inputs.get("lat")
        lng = inputs.get("lng")

        if lat and lng:
            set_location(lat, lng)

        # Emergency check — before LLM call
        emergency_keywords = ["chest pain", "can't breathe", "unconscious", "heart attack", "stroke"]
        if any(kw in inputs["input"].lower() for kw in emergency_keywords):
            return {
                "output": {
                    "type": "alert",
                    "message": "⚠️ This sounds like a medical emergency! Call 911 or your local emergency number immediately.",
                    "data": {},
                }
            }

        messages = [SystemMessage(content=system_prompt)]

        if session_id:
            history = get_memory(session_id)
            for msg in history:
                if msg["sender"] == "client" and msg["message"] != inputs.get("input"):
                    messages.append(HumanMessage(content=msg["message"]))
                elif msg["sender"] == "bot":
                    content = msg["message"]
                    if isinstance(content, dict):
                        content = content.get("message", str(content))
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=inputs["input"]))

        response = _llm_with_tools.invoke(messages)

        # LLM decided to call a tool
        if response.tool_calls:
            call = response.tool_calls[0]
            tool = _tool_map().get(call["name"])
            if tool:
                tool_input = list(call["args"].values())[0] if call["args"] else inputs["input"]
                result = tool.func(tool_input)
                print(f"[AGENT] Tool: {call['name']} | Input: {tool_input}")
                return {"output": result}

        # LLM returned plain text — normalize and wrap
        content = response.content
        if isinstance(content, list):
            content = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            ).strip()

        # Try to parse if LLM returned JSON string
        try:
            parsed = json.loads(content)
            if "type" in parsed and "message" in parsed:
                return {"output": parsed}
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "output": {
                "type": "text",
                "message": content,
                "data": {},
            }
        }

agent = AgentWrapper()
