import requests
import math

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]

def _distance_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

LOW_QUALITY_TERMS = [
    "subcentre",
    "sub centre",
    "sub-center",
    "sub center",
    "dispensary",
    "health centre",
    "health center",
    "urban health centre",
    "urban health center",
    "primary health centre",
    "primary health center",
    "phc",
]

def _is_low_quality_name(name: str) -> bool:
    lowered = name.lower()
    return any(term in lowered for term in LOW_QUALITY_TERMS)

def _dedupe_places(places: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for place in places:
        key = (place.get("name", "").strip().lower(), place.get("vicinity", "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(place)
    return unique

def get_nearby_hospitals(lat: float, lng: float, radius: int = 10000) -> list[dict]:
    query = f"""
[out:json][timeout:15];
(
  node["amenity"="hospital"](around:{radius},{lat},{lng});
  node["amenity"="clinic"](around:{radius},{lat},{lng});
  way["amenity"="hospital"](around:{radius},{lat},{lng});
  way["amenity"="clinic"](around:{radius},{lat},{lng});
);
out center;
"""
    headers = {"User-Agent": "healthcare-chatbot/1.0"}
    for mirror in OVERPASS_MIRRORS:
        try:
            res = requests.get(mirror, params={"data": query}, headers=headers, timeout=20)
            if res.status_code != 200:
                continue
            elements = res.json().get("elements", [])
            hospitals = []
            for place in elements:
                tags = place.get("tags", {})
                name = tags.get("name")
                if not name:
                    continue
                p_lat = place.get("lat") or place.get("center", {}).get("lat")
                p_lon = place.get("lon") or place.get("center", {}).get("lon")
                if not p_lat or not p_lon:
                    continue
                dist = _distance_km(lat, lng, p_lat, p_lon)
                hospitals.append({
                    "name": name,
                    "vicinity": tags.get("addr:street", tags.get("addr:city", "")),
                    "distance_km": dist,
                    "maps_link": f"https://www.google.com/maps?q={p_lat},{p_lon}",
                    "type": tags.get("amenity", "hospital"),
                    "is_low_quality": _is_low_quality_name(name),
                })
            hospitals = _dedupe_places(hospitals)
            hospitals.sort(key=lambda x: (x["type"] != "hospital", x["is_low_quality"], x["distance_km"]))
            strong = [h for h in hospitals if not h["is_low_quality"]]
            return (strong or hospitals)[:5]
        except Exception:
            continue

    raise RuntimeError("All Overpass mirrors failed. Please try again in a moment.")

def _place_from_overpass(place: dict, lat: float, lng: float, default_type: str) -> dict | None:
    tags = place.get("tags", {})
    name = tags.get("name") or tags.get("operator")
    if not name:
        return None

    p_lat = place.get("lat") or place.get("center", {}).get("lat")
    p_lon = place.get("lon") or place.get("center", {}).get("lon")
    if not p_lat or not p_lon:
        return None

    speciality = (
        tags.get("healthcare:speciality")
        or tags.get("speciality")
        or tags.get("medical_system:speciality")
        or ""
    )
    return {
        "name": name,
        "vicinity": tags.get("addr:street", tags.get("addr:city", "")),
        "distance_km": _distance_km(lat, lng, p_lat, p_lon),
        "maps_link": f"https://www.google.com/maps?q={p_lat},{p_lon}",
        "type": tags.get("amenity") or tags.get("healthcare") or default_type,
        "speciality": speciality,
        "phone": tags.get("phone") or tags.get("contact:phone", ""),
        "is_low_quality": _is_low_quality_name(name),
    }

def get_nearby_doctors(lat: float, lng: float, doctor_type: str = "", radius: int = 10000) -> list[dict]:
    query = f"""
[out:json][timeout:15];
(
  node["amenity"="doctors"](around:{radius},{lat},{lng});
  way["amenity"="doctors"](around:{radius},{lat},{lng});
  node["healthcare"="doctor"](around:{radius},{lat},{lng});
  way["healthcare"="doctor"](around:{radius},{lat},{lng});
  node["healthcare"="clinic"](around:{radius},{lat},{lng});
  way["healthcare"="clinic"](around:{radius},{lat},{lng});
  node["amenity"="clinic"](around:{radius},{lat},{lng});
  way["amenity"="clinic"](around:{radius},{lat},{lng});
);
out center;
"""
    keywords = [part.lower() for part in doctor_type.replace("specialist", "").split() if len(part) > 2]
    headers = {"User-Agent": "healthcare-chatbot/1.0"}

    for mirror in OVERPASS_MIRRORS:
        try:
            res = requests.get(mirror, params={"data": query}, headers=headers, timeout=20)
            if res.status_code != 200:
                continue

            places = []
            for place in res.json().get("elements", []):
                item = _place_from_overpass(place, lat, lng, "doctor")
                if not item:
                    continue
                haystack = f"{item['name']} {item['speciality']} {item['type']}".lower()
                item["matches_speciality"] = bool(keywords and any(k in haystack for k in keywords))
                places.append(item)

            places = _dedupe_places(places)
            places.sort(key=lambda x: (x["is_low_quality"], not x["matches_speciality"], x["distance_km"]))
            strong = [p for p in places if not p["is_low_quality"]]
            return (strong or places)[:5]
        except Exception:
            continue

    raise RuntimeError("All Overpass mirrors failed. Please try again in a moment.")
