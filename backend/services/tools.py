from langchain_core.tools import Tool

def find_hospital(location: str) -> str:
    return f"Nearby hospitals in {location}: City Care Hospital, Apollo Clinic."

def suggest_doctor(symptom: str) -> str:
    return (
        f"For {symptom}, it's best to consult a General Physician. "
        "They can assess your symptoms and guide you further."
    )

def health_advice(symptom: str) -> str:
    return (
        f"For {symptom}, make sure to rest well, stay hydrated, and monitor your temperature. "
        "If symptoms persist beyond 2 days, consult a doctor."
    )

tools = [
    Tool(
        name="doctor_suggestion",
        func=suggest_doctor,
        description="""
Use this tool ONLY when the user asks which doctor to consult based on symptoms.
Examples:
- I have fever, which doctor?
- headache doctor?
- cold doctor?
Input should be the symptom like 'fever'
"""
    ),
    Tool(
        name="hospital_finder",
        func=find_hospital,
        description="""
Use this tool when user asks for nearby hospitals.
Examples:
- nearest hospital
- hospital near me
Input should be location
"""
    ),
    Tool(
        name="health_advice",
        func=health_advice,
        description="""
Use this tool for general health advice based on symptoms.
Examples:
- I have fever
- what to do for headache
Input should be symptom
"""
    ),
]
