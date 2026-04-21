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
                })
            hospitals.sort(key=lambda x: x["distance_km"])
            return hospitals[:5]
        except Exception:
            continue

    raise RuntimeError("All Overpass mirrors failed. Please try again in a moment.")
