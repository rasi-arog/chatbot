import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langsmith import traceable
from services.llm import llm
from services.tools import tools, set_location

system_prompt = """You are a friendly healthcare assistant. Use tools ONLY when clearly needed.

Tool usage rules (be strict):
- User explicitly mentions symptoms or asks for health advice → use health_advice tool
- User explicitly asks which doctor or specialist to see → use doctor_suggestion tool
- User explicitly asks for nearby hospital or clinic → use hospital_finder tool
- Emergency (chest pain, can't breathe, unconscious, heart attack, stroke) → respond immediately with type "alert"

Do NOT use any tool for:
- Greetings (hello, hi, how are you)
- Personal info (name, age, location)
- General conversation
- Vague questions not related to health

For non-tool responses, reply in this EXACT JSON format:
{
  "type": "text",
  "message": "<your response here>",
  "data": {}
}

Always add a disclaimer that you do not provide medical diagnosis."""

_llm_with_tools = llm.bind_tools(tools)

def _tool_map():
    return {t.name: t for t in tools}

class AgentWrapper:
    @traceable(name="healthcare-agent")
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
                    "message": "This sounds like a medical emergency! Call 911 or your local emergency number immediately.",
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
                    if not content or not isinstance(content, str):
                        continue
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=inputs["input"]))

        # Only allow tools if message contains health-related keywords
        health_keywords = ["symptom", "fever", "pain", "cough", "cold", "headache", "doctor", "hospital", "clinic", "medicine", "sick", "ill", "disease", "infection", "allergy", "diabetes", "cancer", "anxiety", "depression", "stomach", "chest", "breathing", "rash", "injury", "blood", "heart", "lung", "kidney", "throat", "ear", "eye", "back", "joint", "bone", "pregnancy", "mental", "health", "nearby", "near me", "find"]
        force_no_tools = not any(kw in inputs["input"].lower() for kw in health_keywords)

        response = (_llm_with_tools if not force_no_tools else llm).invoke(messages)

        # Log token usage
        usage = response.response_metadata.get("usage", {}) or response.response_metadata.get("token_usage", {})
        print(f"[TOKEN USAGE] Input: {usage.get('prompt_tokens', 0)}, Output: {usage.get('completion_tokens', 0)}, Total: {usage.get('total_tokens', 0)}")

        # LLM decided to call a tool
        if response.tool_calls:
            call = response.tool_calls[0]
            tool = _tool_map().get(call["name"])
            if tool:
                args = call.get("args", {})
                tool_input = args.get("__arg1") or args.get("query") or (list(args.values())[0] if args else inputs["input"])
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
            # Handle cases where LLM appends JSON after plain text
            json_start = content.find('{')
            if json_start != -1:
                parsed = json.loads(content[json_start:])
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
