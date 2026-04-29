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


# Diet data: symptom_key -> condition -> {eat, avoid, tips}
_DIET_MAP = {
    "default": {
        "diabetes": {
            "eat": ["Vegetable soup", "Green leafy vegetables", "Whole grains (roti, brown rice)", "Apple", "Guava", "Papaya", "Warm lemon water (no sugar)"],
            "avoid": ["Sugar and sweets", "Fruit juices", "White rice in large quantity", "Processed foods"],
            "tips": ["Monitor blood sugar regularly", "Eat small frequent meals", "Stay active with light walks"],
        },
        "bp": {
            "eat": ["Banana (rich in potassium)", "Oats", "Boiled/steamed vegetables", "Low-fat dairy", "Garlic"],
            "avoid": ["Salt-heavy food", "Pickles", "Fried items", "Processed meats", "Caffeine"],
            "tips": ["Limit sodium to under 1500mg/day", "Stay well hydrated", "Avoid stress"],
        },
        "thyroid": {
            "eat": ["Iodine-rich foods (eggs, dairy)", "Selenium-rich foods (Brazil nuts, tuna)", "Fresh fruits and vegetables", "Whole grains"],
            "avoid": ["Raw cruciferous vegetables in excess", "Soy products in excess", "Processed foods"],
            "tips": ["Take thyroid medication on empty stomach", "Maintain consistent meal times"],
        },
        "pcod": {
            "eat": ["High-fiber vegetables", "Whole grains", "Lentils and beans", "Lean protein", "Nuts and seeds", "Low-GI fruits"],
            "avoid": ["Sugary foods", "Refined flour", "Fried snacks", "Sweetened drinks"],
            "tips": ["Keep meal timings regular", "Include daily walking or light exercise", "Discuss cycle changes with a Gynecologist"],
        },
        "cholesterol": {
            "eat": ["Oats", "Barley", "Beans and lentils", "Vegetables", "Fruits", "Nuts in small portions", "Fish or lean protein"],
            "avoid": ["Fried foods", "Butter and ghee in excess", "Processed meats", "Bakery items", "Trans fats"],
            "tips": ["Choose steamed or grilled foods", "Increase soluble fiber", "Check lipid levels as advised by your doctor"],
        },
        "kidney": {
            "eat": ["Fresh low-salt meals", "Rice or roti in moderate portions", "Cooked vegetables as advised", "Apple", "Cabbage", "Cauliflower"],
            "avoid": ["High-salt packaged foods", "Excess protein", "Cola drinks", "Processed meats", "Potassium-heavy foods unless doctor-approved"],
            "tips": ["Kidney diets depend on lab values", "Ask a Nephrologist about protein, potassium, and fluid limits", "Do not start supplements without medical advice"],
        },
        "weight_loss": {
            "eat": ["Vegetables", "Lean protein", "Dal or beans", "Whole grains in measured portions", "Fruit instead of sweets", "Plenty of water"],
            "avoid": ["Sugary drinks", "Deep-fried snacks", "Large late-night meals", "Highly processed foods"],
            "tips": ["Aim for gradual weight loss", "Pair diet with regular activity", "Do not crash diet, especially if you have a medical condition"],
        },
        "none": {
            "eat": ["Khichdi", "Vegetable soup", "Idli", "Coconut water", "Orange", "Apple"],
            "avoid": ["Oily and spicy food", "Heavy meals", "Cold drinks"],
            "tips": ["Drink warm water frequently", "Rest well", "Eat light and easy-to-digest food"],
        },
    },
    "fever": {
        "diabetes": {
            "eat": ["Warm water with lemon (no sugar)", "Vegetable soup", "Green leafy vegetables", "Whole grain roti", "Apple", "Guava", "Papaya"],
            "avoid": ["Sugar and sweets", "Fruit juices", "White rice in large quantity"],
            "tips": ["Monitor blood sugar closely — fever can spike it", "Stay hydrated with sugar-free fluids", "Eat small meals every 3-4 hours"],
        },
        "bp": {
            "eat": ["Banana", "Oats porridge", "Boiled vegetables", "Coconut water (low sodium)", "Warm herbal tea"],
            "avoid": ["Salt-heavy food", "Pickles", "Fried items", "Caffeine"],
            "tips": ["Monitor BP more frequently during fever", "Stay well hydrated", "Rest and avoid exertion"],
        },
        "thyroid": {
            "eat": ["Warm soups", "Eggs (well cooked)", "Fresh fruits", "Whole grains", "Warm water"],
            "avoid": ["Raw cabbage/broccoli in excess", "Soy products", "Cold foods"],
            "tips": ["Continue thyroid medication as prescribed", "Fever can affect thyroid levels — consult doctor if prolonged"],
        },
        "none": {
            "eat": ["Khichdi", "Vegetable soup", "Idli", "Coconut water", "Orange", "Apple"],
            "avoid": ["Oily and spicy food", "Heavy meals", "Cold drinks"],
            "tips": ["Drink warm water frequently", "Rest well", "Monitor temperature every few hours"],
        },
    },
    "cough": {
        "diabetes": {
            "eat": ["Warm turmeric milk (no sugar)", "Ginger tea (no sugar)", "Honey (small amount)", "Warm soups", "Soft cooked vegetables"],
            "avoid": ["Cold drinks", "Ice cream", "Sugary foods", "Dairy in excess"],
            "tips": ["Steam inhalation helps", "Check cough syrups — many contain sugar"],
        },
        "bp": {
            "eat": ["Warm ginger tea", "Honey with warm water", "Vegetable broth (low salt)", "Steamed vegetables"],
            "avoid": ["Salty snacks", "Cold drinks", "Processed foods"],
            "tips": ["Avoid OTC decongestants — they can raise BP", "Steam inhalation is safe"],
        },
        "thyroid": {
            "eat": ["Warm fluids", "Honey", "Ginger tea", "Soft cooked foods"],
            "avoid": ["Cold foods", "Excess dairy", "Raw cruciferous vegetables"],
            "tips": ["Stay warm", "Consult doctor before taking cough medicine with thyroid condition"],
        },
        "none": {
            "eat": ["Warm water with honey and ginger", "Turmeric milk", "Vegetable soup"],
            "avoid": ["Cold drinks", "Ice cream", "Fried food", "Dairy in excess"],
            "tips": ["Gargle with warm salt water", "Stay hydrated", "Avoid cold air"],
        },
    },
    "headache": {
        "diabetes": {
            "eat": ["Water (stay hydrated)", "Magnesium-rich foods (spinach, almonds)", "Whole grains", "Low-GI fruits"],
            "avoid": ["Skipping meals (causes blood sugar drop)", "Caffeine excess", "Sugary foods"],
            "tips": ["Check blood sugar — headache can signal low/high sugar", "Eat regular meals", "Rest in a quiet dark room"],
        },
        "bp": {
            "eat": ["Banana", "Leafy greens", "Water", "Low-sodium foods"],
            "avoid": ["Salt", "Caffeine", "Alcohol", "Processed foods"],
            "tips": ["Check BP immediately", "Rest in a quiet room", "Avoid screen time"],
        },
        "thyroid": {
            "eat": ["Hydrating foods", "Magnesium-rich foods", "Whole grains"],
            "avoid": ["Caffeine", "Processed foods", "Skipping meals"],
            "tips": ["Thyroid imbalance can cause headaches — check levels if frequent", "Rest and stay hydrated"],
        },
        "none": {
            "eat": ["Water", "Ginger tea", "Banana", "Almonds", "Light meals"],
            "avoid": ["Caffeine excess", "Skipping meals", "Bright screens"],
            "tips": ["Rest in a dark quiet room", "Apply cold/warm compress", "Stay hydrated"],
        },
    },
    "stomach": {
        "diabetes": {
            "eat": ["Plain rice (small portion)", "Boiled vegetables", "Plain yogurt (unsweetened)", "Banana", "Warm water"],
            "avoid": ["Spicy food", "Oily food", "Sugary drinks", "Raw vegetables"],
            "tips": ["Eat very small meals", "Monitor blood sugar — stomach issues affect absorption", "Stay hydrated with sugar-free fluids"],
        },
        "bp": {
            "eat": ["Plain rice", "Boiled vegetables", "Banana", "Low-sodium yogurt", "Warm water"],
            "avoid": ["Salty food", "Pickles", "Spicy food", "Fried items"],
            "tips": ["Avoid antacids high in sodium", "Eat small frequent meals", "Stay hydrated"],
        },
        "thyroid": {
            "eat": ["Easy-to-digest foods", "Boiled vegetables", "Plain rice", "Warm soups"],
            "avoid": ["Raw cruciferous vegetables", "High-fiber foods during acute pain", "Spicy food"],
            "tips": ["Thyroid issues can cause digestive problems — consult doctor if persistent"],
        },
        "none": {
            "eat": ["Khichdi", "Plain rice", "Banana", "Yogurt", "Warm water", "Coconut water"],
            "avoid": ["Spicy food", "Oily food", "Caffeine"],
            "tips": ["Eat small meals", "Avoid lying down immediately after eating", "Stay hydrated"],
        },
    },
}

_ALLERGY_KEYWORDS = {
    "seafood": ["prawn", "shrimp", "fish", "seafood", "crab", "lobster", "shellfish"],
    "dairy": ["milk", "dairy", "lactose", "cheese", "butter", "curd", "yogurt allerg"],
    "nuts": ["peanut", "cashew", "almond", "walnut", "nut allerg", "tree nut"],
    "gluten": ["gluten", "wheat allerg", "celiac"],
    "egg": ["egg allerg"],
    "soy": ["soy allerg", "soya allerg"],
}

_ALLERGY_AVOID = {
    "seafood": "All seafood (prawns, fish, crab) — strictly avoid",
    "dairy": "Milk, curd, cheese, butter — avoid all dairy",
    "nuts": "Peanuts, cashews, almonds and all tree nuts — strictly avoid",
    "gluten": "Wheat, roti, bread, pasta — avoid gluten-containing foods",
    "egg": "Eggs and egg-containing products — strictly avoid",
    "soy": "Soy milk, tofu, soya products — strictly avoid",
}


def _resolve_allergies(text: str) -> list:
    text_lower = text.lower()
    found = []
    for allergy, keywords in _ALLERGY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(allergy)
    return found



_CONDITION_LABELS = {
    "diabetes": "Diabetes (Sugar)",
    "bp": "High Blood Pressure",
    "thyroid": "Thyroid",
    "pcod": "PCOD / PCOS",
    "cholesterol": "High Cholesterol",
    "kidney": "Kidney / Renal Concern",
    "weight_loss": "Weight Loss Goal",
    "none": "No specific condition",
}

_CONDITION_KEYWORDS = {
    "diabetes": ["diabetes", "diabetic", "sugar", "blood sugar"],
    "bp": ["bp", "blood pressure", "hypertension", "high bp"],
    "thyroid": ["thyroid", "hypothyroid", "hyperthyroid"],
    "pcod": ["pcod", "pcos", "polycystic"],
    "cholesterol": ["cholesterol", "lipid", "triglyceride"],
    "kidney": ["kidney", "renal", "ckd"],
    "weight_loss": ["weight loss", "lose weight", "obesity", "overweight"],
    "none": ["none", "no condition", "nothing", "normal", "healthy", "no"],
}

_SYMPTOM_CATEGORY_MAP = [
    ("shortness of breath", "cough"),
    ("body pain", "fever"),
    ("dengue", "fever"),
    ("malaria", "fever"),
    ("viral", "fever"),
    ("viral fever", "fever"),
    ("flu", "fever"),
    ("covid", "fever"),
    ("fever", "fever"),
    ("cold", "cough"),
    ("cough", "cough"),
    ("throat", "cough"),
    ("asthma", "cough"),
    ("breathing", "cough"),
    ("migraine", "headache"),
    ("headache", "headache"),
    ("dizziness", "headache"),
    ("stomach", "stomach"),
    ("gas", "stomach"),
    ("acidity", "stomach"),
    ("indigestion", "stomach"),
    ("diarrhea", "stomach"),
    ("constipation", "stomach"),
    ("vomit", "stomach"),
    ("nausea", "stomach"),
]


def _resolve_condition(text: str):
    text_lower = text.lower()
    for condition, keywords in _CONDITION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return condition
    return None


def _resolve_conditions(text: str):
    text_lower = text.lower()
    found = []
    for condition, keywords in _CONDITION_KEYWORDS.items():
        if condition == "none":
            continue
        if any(kw in text_lower for kw in keywords):
            found.append(condition)
    if found:
        return found
    if any(kw in text_lower for kw in _CONDITION_KEYWORDS["none"]):
        return ["none"]
    return []


def _resolve_symptom_key(symptom: str) -> str:
    symptom_lower = symptom.lower()
    for keyword, category in sorted(_SYMPTOM_CATEGORY_MAP, key=lambda x: -len(x[0])):
        if keyword in symptom_lower:
            return category
    return "default"


def _unique(items):
    result = []
    seen = set()
    for item in items:
        normalized = item.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)
    return result


def personalized_diet(query: str) -> dict:
    """query format: 'symptom|condition' e.g. 'fever|diabetes,bp'"""
    parts = query.split("|", 1)
    symptom = parts[0].strip() if parts else query
    condition_raw = parts[1].strip() if len(parts) > 1 else ""

    # Detect allergies from the full query
    allergies = _resolve_allergies(query)

    conditions = _resolve_conditions(condition_raw) if condition_raw else []
    if not conditions:
        conditions = _resolve_conditions(symptom)
    if not conditions:
        conditions = ["none"]

    active_conditions = [c for c in conditions if c != "none"]
    if len(active_conditions) > 3:
        labels = ", ".join(_CONDITION_LABELS.get(c, c.title()) for c in active_conditions)
        return {
            "type": "text",
            "message": f"You mentioned multiple medical conditions ({labels}). For safety, it's best to consult a doctor or dietitian for a personalized diet plan.\n\nI can provide general dietary guidance if you'd like.",
            "data": {"symptom": symptom, "conditions": active_conditions},
        }

    symptom_key = _resolve_symptom_key(symptom)

    diet_source = _DIET_MAP.get(symptom_key, _DIET_MAP["default"])
    diets = [
        diet_source.get(condition)
        or _DIET_MAP["default"].get(condition)
        or _DIET_MAP["default"]["none"]
        for condition in conditions
    ]
    diet = {
        "eat": _unique(item for plan in diets for item in plan["eat"]),
        "avoid": _unique(item for plan in diets for item in plan["avoid"]),
        "tips": _unique(item for plan in diets for item in plan["tips"]),
    }

    # Inject allergy avoids
    for allergy in allergies:
        avoid_str = _ALLERGY_AVOID[allergy]
        if avoid_str.lower() not in [a.lower() for a in diet["avoid"]]:
            diet["avoid"].insert(0, avoid_str)
    if allergies:
        diet["tips"].insert(0, "Avoid all allergens strictly — even small amounts can cause reactions")

    # Build readable labels:
    # - omit the "none" condition label unless it's the only thing we have
    # - avoid polluting the header with raw user sentences (e.g., "I have fever...")
    condition_label = " + ".join(_CONDITION_LABELS.get(c, c.title()) for c in active_conditions)
    allergy_label = " + ".join(a.title() + " Allergy" for a in allergies)
    full_label = " + ".join(filter(None, [condition_label, allergy_label]))
    symptom_label = symptom_key.title() if symptom_key != "default" else "General"

    eat_list = "\n".join(f"- {item}" for item in diet["eat"])
    avoid_list = "\n".join(f"- {item}" for item in diet["avoid"])
    tips_list = "\n".join(f"- {item}" for item in diet["tips"])

    header = f"Personalized Diet Plan - {symptom_label}"
    if full_label:
        header = f"{header} + {full_label}"

    message = (
        f"{header}\n\n"
        f"Eat:\n{eat_list}\n\n"
        f"Avoid:\n{avoid_list}\n\n"
        f"Care Tips:\n{tips_list}\n\n"
        f"This is general dietary guidance. Please consult a doctor for your specific medical condition."
    )

    return {
        "type": "diet_plan",
        "message": message,
        "data": {
            "symptom": symptom,
            "condition": conditions[0],
            "conditions": conditions,
            "condition_label": full_label,
            "allergies": allergies,
            "eat": diet["eat"],
            "avoid": diet["avoid"],
            "tips": diet["tips"],
        },
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
    Tool(
        name="personalized_diet",
        func=personalized_diet,
        description="Use when user provides their medical condition (diabetes, BP, thyroid, PCOD/PCOS, cholesterol, kidney, weight loss, or none) after receiving health advice, OR when user asks for a diet plan. Input format: 'symptom|condition' e.g. 'fever|diabetes', 'dengue|bp', or 'pcod|pcod'.",
    ),
]
