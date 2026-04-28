import threading
from langchain_core.tools import Tool
from services.maps import get_nearby_hospitals, get_nearby_doctors

# Per-request location storage: thread-safe, no shared global state.
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
            "message": "No strong hospital listings were found within 10km. Try again with a larger nearby city or check emergency services if this is urgent.",
            "data": {},
        }
    return {
        "type": "hospital_list",
        "message": f"Found {len(hospitals)} nearby hospital or clinic listings. Please verify availability before visiting.",
        "data": {"hospitals": hospitals},
    }


# Maps specialist names back to canonical form (for chip-triggered lookups)
_SPECIALIST_ALIASES = {
    "general physician": "General Physician",
    "gynecologist": "Gynecologist",
    "gynaecologist": "Gynecologist",
    "pulmonologist": "Pulmonologist",
    "cardiologist": "Cardiologist",
    "dermatologist": "Dermatologist",
    "ophthalmologist": "Ophthalmologist",
    "orthopedic": "Orthopedic",
    "orthopaedic": "Orthopedic",
    "pediatrician": "Pediatrician",
    "dentist": "Dentist",
    "oncologist": "Oncologist",
    "psychiatrist": "Psychiatrist",
    "gastroenterologist": "Gastroenterologist",
    "nephrologist": "Nephrologist",
    "urologist": "Urologist",
    "neurologist": "Neurologist",
    "endocrinologist": "Endocrinologist",
    "ent specialist": "ENT Specialist",
    "hematologist": "Hematologist",
    "allergist": "Allergist",
}

_SYMPTOM_MAP = [
    # Gynecology
    ("pcod", "Gynecologist"),
    ("pcos", "Gynecologist"),
    ("irregular period", "Gynecologist"),
    ("menstrual", "Gynecologist"),
    ("ovary", "Gynecologist"),
    ("uterus", "Gynecologist"),
    ("pregnancy", "Gynecologist"),
    # General
    ("fever", "General Physician"),
    ("flu", "General Physician"),
    ("cold", "General Physician"),
    ("fatigue", "General Physician"),
    ("tired", "General Physician"),
    ("weakness", "General Physician"),
    ("nausea", "General Physician"),
    ("vomit", "General Physician"),
    # Pulmonology
    ("cough", "Pulmonologist"),
    ("asthma", "Pulmonologist"),
    ("lung", "Pulmonologist"),
    ("breathing", "Pulmonologist"),
    ("shortness of breath", "Pulmonologist"),
    # Cardiology
    ("heart", "Cardiologist"),
    ("chest pain", "Cardiologist"),
    ("palpitation", "Cardiologist"),
    # Dermatology
    ("skin", "Dermatologist"),
    ("rash", "Dermatologist"),
    ("acne", "Dermatologist"),
    ("eczema", "Dermatologist"),
    ("psoriasis", "Dermatologist"),
    # Ophthalmology
    ("eye", "Ophthalmologist"),
    ("vision", "Ophthalmologist"),
    ("blurry", "Ophthalmologist"),
    # Orthopedics
    ("bone", "Orthopedic"),
    ("joint", "Orthopedic"),
    ("knee", "Orthopedic"),
    ("shoulder", "Orthopedic"),
    ("fracture", "Orthopedic"),
    ("back pain", "Orthopedic"),
    ("spine", "Orthopedic"),
    # Pediatrics
    ("child", "Pediatrician"),
    ("baby", "Pediatrician"),
    ("infant", "Pediatrician"),
    # Dental
    ("teeth", "Dentist"),
    ("tooth", "Dentist"),
    ("dental", "Dentist"),
    ("gum", "Dentist"),
    # Oncology
    ("cancer", "Oncologist"),
    ("tumor", "Oncologist"),
    # Psychiatry
    ("mental", "Psychiatrist"),
    ("anxiety", "Psychiatrist"),
    ("depression", "Psychiatrist"),
    ("stress", "Psychiatrist"),
    ("insomnia", "Psychiatrist"),
    # Gastroenterology
    ("stomach", "Gastroenterologist"),
    ("digestion", "Gastroenterologist"),
    ("diarrhea", "Gastroenterologist"),
    ("constipation", "Gastroenterologist"),
    ("bloating", "Gastroenterologist"),
    ("liver", "Gastroenterologist"),
    # Nephrology / Urology
    ("kidney", "Nephrologist"),
    ("urine", "Urologist"),
    ("urinary", "Urologist"),
    # Neurology
    ("brain", "Neurologist"),
    ("headache", "Neurologist"),
    ("migraine", "Neurologist"),
    ("seizure", "Neurologist"),
    ("dizziness", "Neurologist"),
    # Endocrinology
    ("diabetes", "Endocrinologist"),
    ("thyroid", "Endocrinologist"),
    ("hormone", "Endocrinologist"),
    # ENT
    ("ear", "ENT Specialist"),
    ("nose", "ENT Specialist"),
    ("throat", "ENT Specialist"),
    ("sinus", "ENT Specialist"),
    ("tonsil", "ENT Specialist"),
    # Hematology / Allergy
    ("blood disorder", "Hematologist"),
    ("allergy", "Allergist"),
    ("allergic", "Allergist"),
]


def _resolve_doctor_type(text: str) -> str:
    text_lower = text.lower()
    # First check if text directly names a specialist (e.g. chip-triggered "Find nearby General Physician doctors")
    for alias, canonical in _SPECIALIST_ALIASES.items():
        if alias in text_lower:
            return canonical
    # Then match by symptom keywords (longer phrases first to avoid partial matches)
    for keyword, doctor in sorted(_SYMPTOM_MAP, key=lambda x: -len(x[0])):
        if keyword in text_lower:
            return doctor
    return "General Physician"


def _wants_nearby_doctors(text: str) -> bool:
    lowered = text.lower()
    nearby_words = ["nearby", "near me", "around me", "find", "show", "search", "list"]
    doctor_words = list(_SPECIALIST_ALIASES.keys()) + ["doctor", "specialist", "clinic"]
    has_nearby = any(word in lowered for word in nearby_words)
    has_doctor = any(word in lowered for word in doctor_words)
    # Also treat bare specialist names as nearby requests when location is available
    is_bare_specialist = any(alias == lowered.strip() for alias in _SPECIALIST_ALIASES)
    return (has_nearby and has_doctor) or is_bare_specialist


def suggest_doctor(symptom: str) -> dict:
    symptom = symptom.strip()
    if not symptom:
        return {
            "type": "text",
            "message": "What kind of doctor are you looking for? Tell me a condition, symptom, or specialty, such as PCOD, knee pain, skin rash, Gynecologist, or Orthopedic.",
            "data": {},
        }

    doctor = _resolve_doctor_type(symptom)

    if _wants_nearby_doctors(symptom):
        lat = getattr(_local, "lat", None)
        lng = getattr(_local, "lng", None)
        if lat is None or lng is None:
            return {
                "type": "doctor_suggestion",
                "message": f"Enable location to see nearby {doctor}s.\n\nThis is not a medical diagnosis.",
                "data": {"doctor_type": doctor, "symptom": symptom, "can_search_nearby": True},
            }
        try:
            doctors = get_nearby_doctors(lat, lng, doctor)
        except RuntimeError as e:
            return {"type": "text", "message": str(e), "data": {}}
        if doctors:
            return {
                "type": "doctor_list",
                "message": f"{doctor}s near your location from map data. Please verify availability before visiting.",
                "data": {"doctor_type": doctor, "symptom": symptom, "doctors": doctors},
            }
        return {
            "type": "doctor_suggestion",
            "message": f"I couldn't find strong nearby {doctor} listings. You may need to check a larger hospital or broaden your search area.",
            "data": {"doctor_type": doctor, "symptom": symptom, "can_search_nearby": True},
        }

    return {
        "type": "doctor_suggestion",
        "message": f"Based on your concern, a {doctor} would be the right specialist to consult.\n\nThis is not a medical diagnosis. Would you like to find one nearby?",
        "data": {"doctor_type": doctor, "symptom": symptom, "can_search_nearby": True},
    }


_ADVICE_MAP = [
    # Sorted longest phrase first to avoid partial matches
    ("chest pain", "Chest pain can be serious. Stop what you're doing, rest, and if it doesn't ease quickly, please seek emergency care immediately."),
    ("shortness of breath", "Difficulty breathing needs prompt attention. Sit upright, stay calm, and see a Pulmonologist or go to emergency care if it worsens."),
    ("back pain", "Rest, apply a heat or cold pack, and avoid heavy lifting for now. If pain shoots down your legs, an Orthopedic specialist should take a look."),
    ("irregular period", "Irregular cycles can have many causes. A Gynecologist can evaluate hormones, lifestyle factors, and give you a proper plan."),
    ("blood disorder", "Blood disorders need specialist evaluation. Please see a Hematologist for proper diagnosis and treatment."),
    ("cancer", "I'm really sorry to hear this. Cancer needs immediate attention. Please see an Oncologist as soon as possible — early care makes a significant difference."),
    ("tumor", "This needs urgent evaluation by an Oncologist. Please don't delay; early assessment is really important here."),
    ("diabetes", "Managing diabetes well makes a big difference. Monitor your blood sugar, follow a low-sugar diet, stay active, and work with an Endocrinologist for a proper plan."),
    ("thyroid", "Thyroid issues can affect energy, weight, and mood. An Endocrinologist can run the right tests and guide your treatment."),
    ("migraine", "Migraines can be debilitating. Rest in a dark, quiet room, stay hydrated, and avoid triggers. A Neurologist can help with a long-term management plan."),
    ("headache", "Try resting in a quiet, dark room, drink water, and avoid screens for a bit. If it's severe or keeps coming back, a Neurologist can help."),
    ("seizure", "Seizures need immediate medical evaluation. Please see a Neurologist as soon as possible and avoid driving or operating machinery."),
    ("dizziness", "Dizziness can have many causes. Rest, avoid sudden movements, and stay hydrated. If it persists, a Neurologist or General Physician can help."),
    ("anxiety", "I hear you — anxiety can be really tough. Deep breathing, mindfulness, good sleep, and cutting back on caffeine can help. A Psychiatrist or counselor can give proper support."),
    ("depression", "I'm glad you reached out. Please talk to someone you trust. Regular exercise and good sleep can help, and a Psychiatrist can give proper support."),
    ("insomnia", "Poor sleep affects everything. Try a consistent sleep schedule, limit screens before bed, and avoid caffeine at night. A Psychiatrist can help if it persists."),
    ("stress", "Chronic stress takes a real toll. Try relaxation techniques, regular exercise, and talking to someone. A Psychiatrist or counselor can provide proper support."),
    ("pcod", "PCOD/PCOS is manageable with the right guidance. A Gynecologist can help with cycles, hormones, and a treatment plan tailored to you."),
    ("pcos", "PCOD/PCOS is manageable with the right guidance. A Gynecologist can help with cycles, hormones, and a treatment plan tailored to you."),
    ("menstrual", "Menstrual concerns are best evaluated by a Gynecologist who can assess your cycle and recommend appropriate care."),
    ("pregnancy", "Prenatal care is very important. Please see a Gynecologist regularly for check-ups and guidance throughout your pregnancy."),
    ("heart", "Heart-related symptoms should never be ignored. Please avoid exertion, stay calm, and see a Cardiologist as soon as you can."),
    ("palpitation", "Heart palpitations can be harmless or a sign of something that needs attention. Avoid caffeine and stress, and see a Cardiologist if they persist."),
    ("asthma", "Avoid known triggers, keep your inhaler accessible, and follow your prescribed plan. A Pulmonologist can help optimize your management."),
    ("cough", "Stay hydrated, avoid cold drinks, and steam inhalation may help. If the cough lasts beyond 2 weeks or has blood, see a Pulmonologist."),
    ("breathing", "Breathing difficulties should not be ignored. Stay calm, sit upright, and see a Pulmonologist if it doesn't resolve quickly."),
    ("fever", "Sorry you're feeling this way. Stay hydrated, rest, and monitor your temperature. If it goes very high or lasts more than 3 days, please see a General Physician."),
    ("flu", "Rest well, stay hydrated, and take paracetamol if needed for fever. If symptoms worsen after a few days, see a General Physician."),
    ("nausea", "Eat small, bland meals, stay hydrated, and avoid strong smells. If nausea is severe or persistent, a General Physician can help."),
    ("vomit", "Stay hydrated with small sips of water or electrolyte drinks. If vomiting is frequent or has blood, seek medical attention promptly."),
    ("fatigue", "Persistent fatigue can have many causes — poor sleep, anaemia, thyroid issues, or more. A General Physician can run the right tests."),
    ("weakness", "General weakness can stem from many causes. Rest, eat well, and see a General Physician if it doesn't improve in a few days."),
    ("allergy", "Avoiding known triggers is the best first step. Keep antihistamines handy if advised by a doctor, and an Allergist can help with a long-term plan."),
    ("allergic", "Identify and avoid your triggers. An Allergist can do proper testing and help you manage allergic reactions effectively."),
    ("rash", "Keep the area clean and avoid scratching. A Dermatologist can identify the cause and recommend the right treatment."),
    ("acne", "Keep your skin clean, avoid touching your face, and use non-comedogenic products. A Dermatologist can provide a proper treatment plan."),
    ("eczema", "Moisturize regularly, avoid harsh soaps, and identify triggers. A Dermatologist can prescribe appropriate treatment."),
    ("skin", "Skin concerns are best evaluated by a Dermatologist who can properly diagnose and treat the condition."),
    ("eye", "Avoid rubbing your eyes and protect them from screens and sunlight. An Ophthalmologist can properly evaluate any eye concern."),
    ("vision", "Changes in vision should be evaluated promptly by an Ophthalmologist to rule out serious conditions."),
    ("fracture", "If you suspect a fracture, immobilize the area and seek emergency care. An Orthopedic specialist will assess and treat it properly."),
    ("joint", "Rest the joint, apply ice, and avoid strain. If pain persists or swelling is significant, an Orthopedic specialist can help."),
    ("bone", "Bone pain or injury needs proper evaluation. An Orthopedic specialist can assess and guide treatment."),
    ("knee", "Rest, ice the knee, and avoid high-impact activity. If pain or swelling persists, an Orthopedic specialist should evaluate it."),
    ("stomach", "Eat light, avoid spicy or oily food, and stay hydrated. If the pain is severe or persistent, a Gastroenterologist can help."),
    ("diarrhea", "Stay well hydrated with water and electrolytes. Avoid dairy and spicy food. See a Gastroenterologist if it lasts more than 2 days."),
    ("constipation", "Increase fiber intake, drink more water, and stay active. If it persists, a Gastroenterologist can help."),
    ("bloating", "Avoid gas-producing foods, eat slowly, and stay active. A Gastroenterologist can help if bloating is frequent or painful."),
    ("kidney", "Stay well hydrated and avoid excessive salt and protein. A Nephrologist can evaluate kidney function and guide treatment."),
    ("urinary", "Drink plenty of water and avoid holding urine. If you have pain or burning, a Urologist can help identify the cause."),
    ("urine", "Changes in urine color, frequency, or pain need evaluation. A Urologist can properly assess and treat urinary concerns."),
    ("ear", "Avoid inserting objects into the ear. If you have pain, discharge, or hearing loss, an ENT Specialist should evaluate it."),
    ("throat", "Gargle with warm salt water, stay hydrated, and avoid cold drinks. If pain is severe or persists beyond 3 days, see an ENT Specialist."),
    ("sinus", "Steam inhalation and saline rinses can help. If sinus pain or congestion persists, an ENT Specialist can provide proper treatment."),
    ("tonsil", "Rest, stay hydrated, and gargle with warm salt water. If tonsil pain is severe or recurring, an ENT Specialist should evaluate it."),
    ("teeth", "Brush gently, avoid very hot or cold foods, and see a Dentist as soon as possible for proper evaluation and treatment."),
    ("dental", "Dental issues are best treated early. See a Dentist for a proper examination and treatment plan."),
    ("child", "Children's health concerns should be evaluated by a Pediatrician who specializes in child health and development."),
    ("baby", "For infant health concerns, always consult a Pediatrician promptly — babies can deteriorate quickly."),
]


def health_advice(symptom: str) -> dict:
    symptom_lower = symptom.lower()
    doctor = _resolve_doctor_type(symptom)
    advice = next(
        (msg for keyword, msg in _ADVICE_MAP if keyword in symptom_lower),
        f"For {symptom}: rest well, stay hydrated, and monitor your symptoms. If symptoms persist beyond 2 days or worsen, please consult a doctor.",
    )
    return {
        "type": "health_advice",
        "message": f"{advice}\n\nDisclaimer: This is general advice, not a medical diagnosis.",
        "data": {"symptom": symptom, "doctor_type": doctor, "can_search_nearby": True},
    }


tools = [
    Tool(
        name="doctor_suggestion",
        func=suggest_doctor,
        description="Use when user asks which doctor or specialist to consult. Input: the symptom, condition, or requested specialty. Only returns nearby doctors when the user explicitly asks for nearby/find/show/list doctors.",
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
