def detect_intent(message):
    msg = message.lower()
    if "fever" in msg:
        return "symptom_check"
    elif "hospital" in msg:
        return "hospital_search"
    elif "doctor" in msg:
        return "doctor_suggestion"
    return "general"

def generate_response(intent):
    responses = {
        "symptom_check": "You may have a viral fever. Drink fluids and rest.",
        "hospital_search": "Nearby hospital: City Care Hospital.",
        "doctor_suggestion": "Recommended: General Physician.",
    }
    return responses.get(intent, "Can you provide more details?")
