#!/usr/bin/env python3
"""
collect_osm_nacional.py — Coleta OSM (Overpass) de terreiros em TODO o Brasil.

Consultas por keyword no nome E por tags religiosas (religion=afro-brazilian...),
cobrindo nodes, ways e relations, em bbox do Brasil continental.

Saída: data/osm_nacional/osm_nacional.geojson (+ raw JSONL por consulta)
Republicável sob ODbL (crédito © OpenStreetMap contributors).

Uso: python3 scripts/collect_osm_nacional.py
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "osm_nacional"
OUT.mkdir(exist_ok=True)

URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# bbox Overpass: sul, oeste, norte, leste (lat,lon,lat,lon)
BR = "-34.0,-74.0,5.5,-32.5"

QUERIES = {
    "candombl": f'[out:json][timeout:180];nwr["name"~"candombl",i]({BR});out center tags;',
    "umbanda": f'[out:json][timeout:180];nwr["name"~"umbanda",i]({BR});out center tags;',
    "terreiro": f'[out:json][timeout:180];nwr["name"~"terreiro",i]({BR});out center tags;',
    "ile_axe": f'[out:json][timeout:180];nwr["name"~"il[eê] ax[eé]",i]({BR});out center tags;',
    "ile_axe_ascii": f'[out:json][timeout:180];nwr["name"~"ile ax",i]({BR});out center tags;',
    "casa_orixas": f'[out:json][timeout:180];nwr["name"~"casa de orix|orix[aá]s?",i]({BR});out center tags;',
    "batuque_jurema_mina": f'[out:json][timeout:180];nwr["name"~"batuque|jurema|tambor de mina|tambor de min[aá]",i]({BR});out center tags;',
    "babalorixa_ialorixa": f'[out:json][timeout:180];nwr["name"~"babalorix|ialorix",i]({BR});out center tags;',
    "religion_tag": f'[out:json][timeout:180];nwr["religion"~"afro|candombl|umbanda|batuque",i]({BR});out center tags;',
    "orixas_names": f'[out:json][timeout:180];nwr["name"~"ogum|oxum|oxossi|xang[oô]|ians[aã]|omulu|oxal[aá]|nanan|exu",i]["amenity"~"place_of_worship|community_centre",i]({BR});out center tags;',
}


def run_query(label, q):
    data = urllib.parse.urlencode({"data": q}).encode()
    for ui, url in enumerate(URLS):
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=data, method="POST")
                req.add_header("User-Agent", "IleAxeMap-LABHD-UFBA/1.0 (research; contato via labhd.ufba.br)")
                with urllib.request.urlopen(req, timeout=300) as resp:
                    result = json.loads(resp.read())
                els = result.get("elements", [])
                (OUT / f"raw_{label}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
                return els
            except Exception as ex:
                print(f"  {label} url{ui} tentativa {attempt+1}: {ex}")
                time.sleep(10 * (attempt + 1))
    return []


def main():
    all_els = {}
    for label, q in QUERIES.items():
        els = run_query(label, q)
        named = 0
        for e in els:
            if "tags" not in e or not e["tags"].get("name"):
                continue
            key = f'{e["type"]}/{e["id"]}'
            if key not in all_els:
                lat = e.get("lat") or (e.get("center") or {}).get("lat")
                lon = e.get("lon") or (e.get("center") or {}).get("lon")
                all_els[key] = {"el": e, "lat": lat, "lon": lon}
                named += 1
        print(f"{label}: {len(els)} elementos, {named} novos com nome")

    feats = []
    for key, info in all_els.items():
        e = info["el"]
        t = e["tags"]
        if info["lat"] is None:
            continue
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [info["lon"], info["lat"]]},
            "properties": {
                "osm_id": key, "nome": t.get("name"), "religion": t.get("religion"),
                "amenity": t.get("amenity"), "denomination": t.get("denomination"),
                "endereco": t.get("addr:street"), "cidade": t.get("addr:city"),
                "uf": t.get("addr:state"), "fonte": "osm",
                "geo_status": "fonte_propria_osm",
            },
        })
    fc = {"type": "FeatureCollection", "features": feats}
    (OUT / "osm_nacional.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    print(f"\nTOTAL: {len(feats)} features únicas salvas em {OUT/'osm_nacional.geojson'}")


if __name__ == "__main__":
    main()