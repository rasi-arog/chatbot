import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langsmith import traceable
from services.llm import llm
from services.tools import tools, set_location, personalized_diet, _resolve_conditions, _resolve_symptom_key

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
- User asks which doctor/specialist, or gives a condition/specialty in specialist flow → doctor_suggestion tool
- The doctor_suggestion tool should identify the right specialist first. Only show nearby doctor results when the user explicitly asks for nearby/find/show/list doctors.
- User asks for nearby hospital/clinic → hospital_finder tool
- Emergency (chest pain, can't breathe, unconscious, heart attack, stroke) → type "alert" immediately
- After giving health_advice, ask for conditions ONLY if the user provided symptoms but did NOT provide any known condition yet, and the user is not explicitly asking for a diet/food plan.
- If user already mentions both symptom and condition, directly call personalized_diet without asking again.
- If the user explicitly asks for a diet/food plan, never ask for more conditions; route directly to personalized_diet.
- User replies with a condition (diabetes, BP, thyroid, PCOD/PCOS, cholesterol, kidney, weight loss, none) after health advice → personalized_diet tool. Input: 'symptom|condition' e.g. 'fever|diabetes'
- User explicitly asks for a diet plan → personalized_diet tool

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


def _wants_diet(text: str) -> bool:
    lowered = text.lower()
    diet_words = ["diet", "food", "eat", "meal", "nutrition", "suggest a diet", "diet plan", "what to eat"]
    return any(word in lowered for word in diet_words)


def _condition_only_reply(text: str) -> bool:
    stripped = text.strip()
    if not stripped or not _resolve_conditions(stripped):
        return False
    return len(stripped.replace(",", " ").replace("+", " ").split()) <= 5


def _has_symptom_and_condition(text: str) -> bool:
    # Must have BOTH a known symptom category AND a known condition — not just one
    has_condition = bool(_resolve_conditions(text))
    has_symptom = _resolve_symptom_key(text) != "default"
    return has_condition and has_symptom


def _has_allergy(text: str) -> bool:
    from services.tools import _ALLERGY_KEYWORDS
    lowered = text.lower()
    return any(
        any(kw in lowered for kw in kws)
        for kws in _ALLERGY_KEYWORDS.values()
    )


def _previous_user_symptom(history, current_input: str) -> str:
    for msg in reversed(history):
        if msg.get("sender") != "client":
            continue
        message = msg.get("message", "")
        if not message or message == current_input:
            continue
        if message.lower().startswith("diet:") or _condition_only_reply(message):
            continue
        return message
    return ""


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
        history = get_memory(session_id) if session_id else []

        emergency_keywords = ["chest pain", "can't breathe", "unconscious", "heart attack", "stroke"]
        if any(kw in inputs["input"].lower() for kw in emergency_keywords):
            return {
                "output": {
                    "type": "alert",
                    "message": "⚠️ This sounds like a medical emergency! Please call 911 or your local emergency number immediately. Do not wait.",
                    "data": {},
                }
            }

        # Deterministic diet route from the UI: "diet:symptom|condition".
        if inputs["input"].lower().startswith("diet:"):
            query = inputs["input"].split(":", 1)[1].strip()
            return {"output": personalized_diet(query)}

        # Condition-only reply after a previous symptom message
        if _condition_only_reply(inputs["input"]):
            previous_symptom = _previous_user_symptom(history, inputs["input"])
            if previous_symptom:
                return {"output": personalized_diet(f"{previous_symptom}|{inputs['input']}")}

        # Priority diet routing:
        # - If user asks for diet/food/eat, use personalized_diet
        if _wants_diet(inputs["input"]):
            return {"output": personalized_diet(inputs["input"])}

        # - If user mentions allergies, use personalized_diet (diet plan will include avoid list)
        if _has_allergy(inputs["input"]):
            return {"output": personalized_diet(inputs["input"])}

        # - If user mentions known medical conditions, use personalized_diet
        found_conditions = _resolve_conditions(inputs["input"]) or []
        active_conditions = [c for c in found_conditions if c != "none"]
        if active_conditions:
            return {"output": personalized_diet(inputs["input"])}

        # Route to diet if user mentions both a symptom category AND a condition
        if _has_symptom_and_condition(inputs["input"]):
            return {"output": personalized_diet(inputs["input"])}

        messages = [SystemMessage(content=system_prompt)]

        # Build conversation history — include image analysis context
        if session_id:
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
            "nausea", "vomit", "dizziness", "swelling", "wound", "scar", "prescribed", "prescription",
            "pcod", "pcos", "period", "menstrual", "gynecologist", "gynaecologist", "orthopedic",
            "dermatologist", "cardiologist", "neurologist", "dentist", "pediatrician",
            "diet", "food", "eat", "nutrition", "bp", "blood pressure", "hypertension", "thyroid",
            "diabetic", "sugar", "none", "no condition", "cholesterol", "lipid", "kidney", "renal",
            "weight loss", "lose weight", "obesity", "overweight"
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
                # Safety override:
                # If the user context indicates they want a diet (allergy/conditions/diet request),
                # but the model picked `health_advice`, force `personalized_diet`.
                if call.get("name") == "health_advice":
                    user_text = inputs["input"]
                    wants_diet = _wants_diet(user_text)
                    has_allergy = _has_allergy(user_text)
                    found_conditions = _resolve_conditions(user_text) or []
                    active_conditions = [c for c in found_conditions if c != "none"]
                    if wants_diet or has_allergy or active_conditions:
                        return {"output": personalized_diet(user_text)}

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
