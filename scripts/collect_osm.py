import urllib.request
import urllib.parse
import json
import time

queries = {
    "candombl": '[out:json][timeout:60];area["ISO3166-2"="BR-BA"]->.bahia;node["name"~"candombl",i](area.bahia);out body;',
    "terreiro": '[out:json][timeout:60];area["ISO3166-2"="BR-BA"]->.bahia;node["name"~"terreiro",i](area.bahia);out body;',
    "ilê axé": '[out:json][timeout:60];area["ISO3166-2"="BR-BA"]->.bahia;node["name"~"il[eê] ax[eé]",i](area.bahia);out body;',
    "ile axe": '[out:json][timeout:60];area["ISO3166-2"="BR-BA"]->.bahia;node["name"~"il[ee] ax[ee]",i](area.bahia);out body;',
    "place_of_worship afro": '[out:json][timeout:60];area["ISO3166-2"="BR-BA"]->.bahia;node["amenity"="place_of_worship"]["religion"~"afro|candombl",i](area.bahia);out body;',
    "ogum": '[out:json][timeout:60];area["ISO3166-2"="BR-BA"]->.bahia;node["name"~"ogum|oxum|oxossi|xango|iansa|omulu|oxala|nanan",i](area.bahia);out body;',
    "rocambole": '[out:json][timeout:60];area["ISO3166-2"="BR-BA"]->.bahia;node["name"~"rocambole",i](area.bahia);out body;',
}

url = "https://overpass-api.de/api/interpreter"
all_results = []

for label, query in queries.items():
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("User-Agent", "TerreiroMap/1.0 (LABHD/UFBA research)")
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
            elements = result.get("elements", [])
            named = [e for e in elements if e.get("tags", {}).get("name")]
            print(f"\n=== {label}: {len(elements)} elementos ({len(named)} com nome) ===")
            for e in named[:10]:
                tags = e.get("tags", {})
                print(f"  {tags.get('name','?')} | rel={tags.get('religion','?')} | amenity={tags.get('amenity','?')} | {e.get('lat','?')},{e.get('lon','?')}")
            all_results.extend(elements)
            break
        except Exception as ex:
            print(f"  {label} tentativa {attempt+1}: {ex}")
            if attempt < 2:
                time.sleep(5)

# Deduplicar por ID
seen = set()
unique = []
for e in all_results:
    key = (e["type"], e["id"])
    if key not in seen:
        seen.add(key)
        unique.append(e)

print(f"\n\n=== TOTAL ÚNICO: {len(unique)} elementos ===")
# Salvar GeoJSON
features = []
for e in unique:
    tags = e.get("tags", {})
    if e.get("lat") and e.get("lon"):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [e["lon"], e["lat"]]},
            "properties": {**tags, "osm_id": e["id"], "osm_type": e["type"]}
        })

geojson = {"type": "FeatureCollection", "features": features}
with open("/tmp/terreiros_bahia_osm.geojson", "w") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)
print(f"GeoJSON salvo: /tmp/terreiros_bahia_osm.geojson ({len(features)} features)")