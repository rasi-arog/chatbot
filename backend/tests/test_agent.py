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

# --- Image classification ---

def test_image_verify_invalid_path():
    from services.image_verify import verify_image
    with pytest.raises(ValueError, match="Invalid file path"):
        verify_image("/nonexistent/path.jpg")
