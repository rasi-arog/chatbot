import pytest
from unittest.mock import patch, MagicMock
from services.agent import AgentWrapper

agent = AgentWrapper()

def _mock_llm_response(content: str, tool_calls=None):
    mock = MagicMock()
    mock.content = content
    mock.tool_calls = tool_calls or []
    mock.response_metadata = {"usage": {}}
    return mock

# --- Emergency ---

def test_emergency_chest_pain():
    result = agent.invoke({"input": "I have chest pain", "session_id": None})
    assert result["output"]["type"] == "alert"

def test_emergency_heart_attack():
    result = agent.invoke({"input": "I think I'm having a heart attack", "session_id": None})
    assert result["output"]["type"] == "alert"

def test_emergency_stroke():
    result = agent.invoke({"input": "someone had a stroke", "session_id": None})
    assert result["output"]["type"] == "alert"

# --- Tool routing ---

@patch("services.agent._llm_with_tools")
def test_routes_to_health_advice_tool(mock_llm):
    mock_call = {"name": "health_advice", "args": {"__arg1": "fever"}}
    mock_llm.invoke.return_value = _mock_llm_response("", tool_calls=[mock_call])
    result = agent.invoke({"input": "I have fever", "session_id": None})
    assert result["output"]["type"] == "health_advice"

@patch("services.agent._llm_with_tools")
def test_routes_to_doctor_suggestion_tool(mock_llm):
    mock_call = {"name": "doctor_suggestion", "args": {"__arg1": "headache"}}
    mock_llm.invoke.return_value = _mock_llm_response("", tool_calls=[mock_call])
    result = agent.invoke({"input": "which doctor for headache", "session_id": None})
    assert result["output"]["type"] == "doctor_suggestion"

@patch("services.agent._llm_with_tools")
def test_routes_to_hospital_finder_tool(mock_llm):
    mock_call = {"name": "hospital_finder", "args": {"__arg1": "nearby hospital"}}
    mock_llm.invoke.return_value = _mock_llm_response("", tool_calls=[mock_call])
    with patch("services.tools._local") as mock_local:
        mock_local.lat = 12.9716
        mock_local.lng = 77.5946
        result = agent.invoke({"input": "find nearby hospital", "session_id": None, "lat": 12.9716, "lng": 77.5946})
    assert result["output"]["type"] in ("hospital_list", "text")

def test_direct_diet_command_skips_llm():
    result = agent.invoke({"input": "diet:dengue|diabetes", "session_id": None})
    assert result["output"]["type"] == "diet_plan"
    assert result["output"]["data"]["condition"] == "diabetes"

def test_natural_language_diet_request_skips_llm():
    result = agent.invoke({"input": "I have fever and diabetes, give me diet", "session_id": None})
    assert result["output"]["type"] == "diet_plan"
    assert result["output"]["data"]["conditions"] == ["diabetes"]

def test_symptom_with_conditions_skips_llm():
    result = agent.invoke({"input": "I have fever, diabetes and BP", "session_id": None})
    assert result["output"]["type"] == "diet_plan"
    assert result["output"]["data"]["conditions"] == ["diabetes", "bp"]

def test_allergy_routing_to_personalized_diet():
    result = agent.invoke({"input": "I have fever and allergic to prawns, suggest a diet", "session_id": None})
    assert result["output"]["type"] == "diet_plan"
    assert "seafood" in result["output"]["data"]["allergies"]
    assert any("All seafood" in item for item in result["output"]["data"]["avoid"])
    assert "No specific condition" not in result["output"]["message"]

def test_condition_routing_to_personalized_diet_without_explicit_diet_request():
    result = agent.invoke({"input": "I have diabetes and cholesterol", "session_id": None})
    assert result["output"]["type"] == "diet_plan"
    assert set(result["output"]["data"]["conditions"]) == {"diabetes", "cholesterol"}

def test_too_many_conditions_returns_safe_text():
    result = agent.invoke({"input": "fever diabetes bp thyroid cholesterol kidney", "session_id": None})
    assert result["output"]["type"] == "text"
    assert "multiple medical conditions" in result["output"]["message"].lower()

def test_condition_reply_uses_previous_symptom():
    from services.memory import save_to_memory, clear_memory
    session_id = "test-condition-reply"
    clear_memory(session_id)
    save_to_memory(session_id, {"sender": "client", "message": "I have fever"})
    result = agent.invoke({"input": "Diabetes", "session_id": session_id})
    clear_memory(session_id)
    assert result["output"]["type"] == "diet_plan"
    assert result["output"]["data"]["condition"] == "diabetes"
    assert result["output"]["data"]["symptom"] == "I have fever"

# --- Plain text response ---

@patch("services.agent.llm")
def test_plain_text_response(mock_llm):
    mock_llm.invoke.return_value = _mock_llm_response(
        '{"type": "text", "message": "Hi there!", "data": {}}'
    )
    result = agent.invoke({"input": "hello", "session_id": None})
    assert result["output"]["type"] == "text"
    assert result["output"]["message"] == "Hi there!"

@patch("services.agent.llm")
def test_unwraps_nested_json_message(mock_llm):
    mock_llm.invoke.return_value = _mock_llm_response(
        '{"type": "text", "message": "{\\"type\\": \\"text\\", \\"message\\": \\"Actual message\\", \\"data\\": {}}", "data": {}}'
    )
    result = agent.invoke({"input": "hello", "session_id": None})
    assert result["output"]["message"] == "Actual message"

@patch("services.agent.llm")
def test_fallback_raw_text(mock_llm):
    mock_llm.invoke.return_value = _mock_llm_response("Just a plain response")
    result = agent.invoke({"input": "hello", "session_id": None})
    assert result["output"]["type"] == "text"
    assert "plain response" in result["output"]["message"]

# --- Tools unit tests ---

def test_health_advice_fever():
    from services.tools import health_advice
    result = health_advice("fever")
    assert result["type"] == "health_advice"
    assert "hydrated" in result["message"].lower()
    assert "Disclaimer" in result["message"]

def test_health_advice_unknown_symptom():
    from services.tools import health_advice
    result = health_advice("xyz unknown thing")
    assert result["type"] == "health_advice"
    assert "consult a doctor" in result["message"].lower()

def test_suggest_doctor_known():
    from services.tools import suggest_doctor
    result = suggest_doctor("I have a headache")
    assert result["type"] == "doctor_suggestion"
    assert result["data"]["doctor_type"] == "Neurologist"

def test_suggest_doctor_unknown():
    from services.tools import suggest_doctor
    result = suggest_doctor("something random")
    assert result["type"] == "doctor_suggestion"
    assert result["data"]["doctor_type"] == "General Physician"

def test_find_hospital_no_location():
    from services.tools import find_hospital
    result = find_hospital("hospital near me")
    assert result["type"] == "text"
    assert "location" in result["message"].lower()

def test_personalized_diet_maps_disease_category():
    from services.tools import personalized_diet
    result = personalized_diet("dengue|bp")
    assert result["type"] == "diet_plan"
    assert result["data"]["condition"] == "bp"
    assert "Banana" in result["data"]["eat"]

def test_personalized_diet_supports_new_conditions():
    from services.tools import personalized_diet
    result = personalized_diet("pcod|pcos")
    assert result["type"] == "diet_plan"
    assert result["data"]["condition"] == "pcod"
    assert "High-fiber vegetables" in result["data"]["eat"]

def test_personalized_diet_combines_multiple_conditions():
    from services.tools import personalized_diet
    result = personalized_diet("fever|diabetes,bp")
    assert result["type"] == "diet_plan"
    assert result["data"]["conditions"] == ["diabetes", "bp"]
    assert "Sugar and sweets" in result["data"]["avoid"]
    assert "Salt-heavy food" in result["data"]["avoid"]

def test_personalized_diet_limits_too_many_conditions():
    from services.tools import personalized_diet
    result = personalized_diet("fever|diabetes,bp,thyroid,kidney")
    assert result["type"] == "text"
    assert "multiple medical conditions" in result["message"].lower()

def test_personalized_diet_unknown_is_safe_fallback():
    from services.tools import personalized_diet
    result = personalized_diet("rare unknown condition|none")
    assert result["type"] == "diet_plan"
    assert "Personalized Diet Plan" in result["message"]

# --- Image classification ---

def test_image_verify_invalid_path():
    from services.image_verify import verify_image
    with pytest.raises(ValueError, match="Invalid file path"):
        verify_image("/nonexistent/path.jpg")
