import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langsmith import traceable
from services.llm import llm
from services.tools import tools, set_location

system_prompt = """You are a warm, empathetic healthcare assistant. You help users understand their health concerns, guide them to the right care, and support them — like a knowledgeable friend, not a cold robot.

CONVERSATION STYLE:
- Be warm, natural, and human — never robotic or mechanical
- Ask follow-up questions to understand the user better
- If user says "I feel sick" or is vague → ask what symptoms they have, how long, etc.
- Remember context from earlier in the conversation and refer back to it
- If user uploaded an image earlier in this session, you know about it — reference it naturally
- NEVER say "I cannot diagnose" and stop — always follow up with care and guidance
- NEVER be dismissive — always acknowledge how the user feels first
- If user asks what disease they have → say something like "I'm not able to diagnose, but let me help you understand your symptoms better. Can you tell me more?"

TOOL USAGE (use only when clearly needed):
- Symptoms or health advice requested → health_advice tool
- User asks which doctor/specialist → doctor_suggestion tool
- User asks for nearby hospital/clinic → hospital_finder tool
- Emergency (chest pain, can't breathe, unconscious, heart attack, stroke) → type "alert" immediately

DO NOT use tools for:
- Greetings, small talk, personal info
- Vague non-health questions

RESPONSE FORMAT for non-tool replies — EXACT JSON:
{
  "type": "text",
  "message": "<your response>",
  "data": {}
}

SAFETY: Never provide a diagnosis. Always recommend consulting a doctor for serious concerns. Add a brief disclaimer only when giving health advice."""

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
                    "message": "⚠️ This sounds like a medical emergency! Please call 911 or your local emergency number immediately. Do not wait.",
                    "data": {},
                }
            }

        messages = [SystemMessage(content=system_prompt)]

        # Build conversation history — include image analysis context
        if session_id:
            history = get_memory(session_id)
            for msg in history:
                if msg["sender"] == "client":
                    if msg["message"] and msg["message"] != inputs.get("input"):
                        content = msg["message"]
                        if msg.get("type") == "image_file":
                            content = f"[User uploaded an image: {content}]"
                        messages.append(HumanMessage(content=content))
                elif msg["sender"] == "bot":
                    content = msg.get("message", "")
                    if msg.get("type") == "image_analysis" and msg.get("image_summary"):
                        content = f"[Image analysis result: {msg['image_summary']}]"
                    if not content or not isinstance(content, str):
                        continue
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=inputs["input"]))

        # Only allow tools if message contains health-related keywords
        health_keywords = [
            "symptom", "fever", "pain", "cough", "cold", "headache", "doctor", "hospital",
            "clinic", "medicine", "sick", "ill", "disease", "infection", "allergy", "diabetes",
            "cancer", "anxiety", "depression", "stomach", "chest", "breathing", "rash", "injury",
            "blood", "heart", "lung", "kidney", "throat", "ear", "eye", "back", "joint", "bone",
            "pregnancy", "mental", "health", "nearby", "near me", "find", "tired", "fatigue",
            "nausea", "vomit", "dizziness", "swelling", "wound", "scar", "prescribed", "prescription"
        ]
        force_no_tools = not any(kw in inputs["input"].lower() for kw in health_keywords)

        response = (_llm_with_tools if not force_no_tools else llm).invoke(messages)

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

        content = response.content
        if isinstance(content, list):
            content = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            ).strip()

        try:
            json_start = content.find('{')
            if json_start != -1:
                parsed = json.loads(content[json_start:])
                if "type" in parsed and "message" in parsed:
                    # Unwrap if message is itself a JSON string
                    msg = parsed["message"]
                    if isinstance(msg, str):
                        try:
                            inner = json.loads(msg)
                            if "message" in inner:
                                parsed["message"] = inner["message"]
                        except (json.JSONDecodeError, TypeError):
                            pass
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
