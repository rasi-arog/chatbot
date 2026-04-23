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
            "message": "I need your location to find nearby hospitals. Please enable location access and try again.",
            "data": {},
        }
    try:
        hospitals = get_nearby_hospitals(lat, lng)
    except RuntimeError as e:
        return {"type": "text", "message": str(e), "data": {}}
    if not hospitals:
        return {
            "type": "text",
            "message": "No hospitals found within 10km of your location.",
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
            "message": "Based on what you've described, a General Physician would be a good first step. They'll assess you properly and refer you to the right specialist if needed.",
            "data": {"doctor_type": "General Physician", "symptom": symptom},
        }
    return {
        "type": "doctor_suggestion",
        "message": f"For {symptom}, a {doctor} would be the right person to see. They specialize in exactly this area and can give you proper guidance.",
        "data": {"doctor_type": doctor, "symptom": symptom},
    }

def health_advice(symptom: str) -> dict:
    symptom_lower = symptom.lower()
    advice_map = {
        "cancer": "I'm really sorry to hear this. Cancer needs immediate attention — please see an Oncologist as soon as possible. Early care makes a significant difference, and you don't have to face this alone.",
        "tumor": "This needs urgent evaluation by an Oncologist. Please don't delay — early assessment is really important here.",
        "heart": "Heart-related symptoms should never be ignored. Please avoid exertion, stay calm, and see a Cardiologist as soon as you can.",
        "chest pain": "Chest pain can be serious. Stop what you're doing, rest, and if it doesn't ease up quickly, please seek emergency care.",
        "diabetes": "Managing diabetes well makes a huge difference. Monitor your blood sugar regularly, follow a low-sugar diet, stay active, and work with an Endocrinologist for a proper plan.",
        "fever": "Sorry you're feeling this way. Stay hydrated, get plenty of rest, and paracetamol can help bring the fever down. If it goes above 103°F or lasts more than 3 days, please see a doctor.",
        "headache": "That sounds uncomfortable. Try resting in a quiet, dark room, drink water, and avoid screens for a bit. If it's severe or keeps coming back, a Neurologist can help.",
        "cough": "Stay hydrated, avoid cold drinks, and steam inhalation can really help. If the cough sticks around beyond 2 weeks, it's worth seeing a Pulmonologist.",
        "anxiety": "I hear you — anxiety can be really tough. Deep breathing and mindfulness exercises help a lot. Cutting back on caffeine also makes a difference. Speaking to a Psychiatrist or counselor can give you proper support.",
        "depression": "I'm glad you reached out. Please talk to someone you trust — you don't have to go through this alone. Regular exercise and good sleep help, and a Psychiatrist can give you the right support.",
        "allergy": "Avoiding your known triggers is the best first step. Keep antihistamines handy, and an Allergist can help you build a long-term plan.",
        "stomach": "Eat light, avoid spicy or oily food, and keep yourself hydrated. If the pain is severe or doesn't go away, a Gastroenterologist can help figure out what's going on.",
        "back pain": "Rest up, apply a heat or cold pack, and avoid heavy lifting for now. If the pain is shooting down your legs, an Orthopedic specialist should take a look.",
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
