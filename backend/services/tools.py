import threading
from langchain_core.tools import Tool
from services.maps import get_nearby_hospitals

# Per-request location storage — thread-safe, no shared global state
_local = threading.local()

def set_location(lat: float, lng: float):
    _local.lat = lat
    _local.lng = lng

def find_hospital(query: str) -> dict:
    lat = getattr(_local, "lat", None)
    lng = getattr(_local, "lng", None)
    if lat is None or lng is None:
        return {
            "type": "text",
            "message": "📍 I need your location to find nearby hospitals. Please enable location access and try again.",
            "data": {},
        }
    try:
        hospitals = get_nearby_hospitals(lat, lng)
    except RuntimeError as e:
        return {"type": "text", "message": str(e), "data": {}}
    if not hospitals:
        return {
            "type": "text",
            "message": "No hospitals found within 5km of your location.",
            "data": {},
        }
    return {
        "type": "hospital_list",
        "message": f"Found {len(hospitals)} hospitals near you.",
        "data": {"hospitals": hospitals},
    }

def suggest_doctor(symptom: str) -> dict:
    symptom_map = {
        "fever": "General Physician",
        "cold": "General Physician",
        "cough": "Pulmonologist",
        "heart": "Cardiologist",
        "chest": "Cardiologist",
        "skin": "Dermatologist",
        "rash": "Dermatologist",
        "eye": "Ophthalmologist",
        "vision": "Ophthalmologist",
        "bone": "Orthopedic",
        "joint": "Orthopedic",
        "child": "Pediatrician",
        "baby": "Pediatrician",
        "teeth": "Dentist",
        "dental": "Dentist",
        "cancer": "Oncologist",
        "tumor": "Oncologist",
        "mental": "Psychiatrist",
        "anxiety": "Psychiatrist",
        "depression": "Psychiatrist",
        "stomach": "Gastroenterologist",
        "digestion": "Gastroenterologist",
        "kidney": "Nephrologist",
        "urine": "Urologist",
        "brain": "Neurologist",
        "headache": "Neurologist",
        "migraine": "Neurologist",
        "diabetes": "Endocrinologist",
        "thyroid": "Endocrinologist",
        "lung": "Pulmonologist",
        "breathing": "Pulmonologist",
        "ear": "ENT Specialist",
        "nose": "ENT Specialist",
        "throat": "ENT Specialist",
        "blood": "Hematologist",
        "allergy": "Allergist",
        "pregnancy": "Gynecologist",
        "women": "Gynecologist",
    }
    symptom_lower = symptom.lower()
    doctor = next((v for k, v in symptom_map.items() if k in symptom_lower), None)

    if not doctor:
        return {
            "type": "doctor_suggestion",
            "message": "I recommend visiting a General Physician first. They can assess your condition and refer you to the right specialist.",
            "data": {"doctor_type": "General Physician", "symptom": symptom},
        }
    return {
        "type": "doctor_suggestion",
        "message": f"For {symptom}, you should consult a {doctor}.",
        "data": {"doctor_type": doctor, "symptom": symptom},
    }

def health_advice(symptom: str) -> dict:
    symptom_lower = symptom.lower()
    advice_map = {
        "cancer": "Cancer requires immediate medical attention. Please consult an Oncologist as soon as possible. Do not self-medicate. Early diagnosis significantly improves outcomes.",
        "tumor": "A tumor needs urgent evaluation by an Oncologist. Please seek medical care immediately.",
        "heart": "Heart-related symptoms need urgent attention. Avoid physical exertion, stay calm, and consult a Cardiologist immediately.",
        "chest pain": "Chest pain can be serious. Stop activity, rest, and seek emergency care if it persists.",
        "diabetes": "Monitor your blood sugar regularly, follow a low-sugar diet, stay active, and consult an Endocrinologist for a proper management plan.",
        "fever": "Stay hydrated, rest well, and take paracetamol if needed. If fever exceeds 103°F or lasts more than 3 days, see a doctor.",
        "headache": "Rest in a quiet dark room, stay hydrated, and avoid screen time. If severe or recurring, consult a Neurologist.",
        "cough": "Stay hydrated, avoid cold drinks, and try steam inhalation. If cough persists beyond 2 weeks, see a Pulmonologist.",
        "anxiety": "Practice deep breathing and mindfulness. Reduce caffeine intake. Consider speaking to a Psychiatrist or counselor.",
        "depression": "Reach out to someone you trust. Regular exercise and sleep help. Please consult a Psychiatrist for proper support.",
        "allergy": "Avoid known triggers, keep antihistamines handy, and consult an Allergist for a long-term plan.",
        "stomach": "Eat light, avoid spicy food, stay hydrated. If pain is severe or persistent, consult a Gastroenterologist.",
        "back pain": "Rest, apply heat/cold packs, and avoid heavy lifting. If pain radiates to legs, see an Orthopedic specialist.",
    }
    advice = next(
        (v for k, v in advice_map.items() if k in symptom_lower),
        f"For {symptom}: rest well, stay hydrated, and monitor your symptoms. If symptoms persist beyond 2 days, please consult a doctor."
    )
    return {
        "type": "health_advice",
        "message": f"{advice}\n\n⚠️ Disclaimer: This is general advice, not a medical diagnosis.",
        "data": {"symptom": symptom},
    }

tools = [
    Tool(
        name="doctor_suggestion",
        func=suggest_doctor,
        description="Use when user asks which doctor or specialist to consult. Input: the symptom or condition mentioned by the user.",
    ),
    Tool(
        name="hospital_finder",
        func=find_hospital,
        description="Use when user asks for nearby hospitals or clinics. Input: the user's query string.",
    ),
    Tool(
        name="health_advice",
        func=health_advice,
        description="Use when user describes symptoms or asks for health advice. Input: the symptom or condition.",
    ),
]
