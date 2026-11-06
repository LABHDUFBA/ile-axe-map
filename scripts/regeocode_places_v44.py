#!/usr/bin/env python3
"""Candidata v4.4: re-geocodificação conservadora com Places API (New).

Parte da v4.2, nunca altera dados publicados. Alvos: Mapeando Axé com
coordenada >60 km do município declarado e registros coordenada_agua.

Aceita resultado apenas se: Place API classifica como place_of_worship,
há ao menos 2 tokens distintivos compartilhados e cobertura nominal >=50%,
e a coordenada é coerente com o território esperado. Para SEFAZ sem
município, o território esperado é Salvador, BA, com raio máximo de 35 km.

Uso: GMAPS_API_KEY=... python3 scripts/regeocode_places_v44.py
"""
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/v4_2/terreiros_nacional_v4_2.geojson"
MUNS = ROOT / "data/v4_2/municipios_coords.json"
OUT_DIR = ROOT / "data/v4_4"
CACHE = ROOT / "data/places_cache_v44.json"  # gitignored, contém Place IDs/endereço
PAUSE_S = 0.11

STOP = {
    "a", "as", "o", "os", "de", "da", "das", "do", "dos", "e", "em", "para", "com",
    "ile", "yle", "ile", "axe", "ase", "asa", "terreiro", "casa", "centro", "espirita",
    "umbanda", "candomble", "religioso", "religiosa", "afro", "africano", "africana",
}
GENERICOS = ("sem nome", "terreiro sem", "casa sem")


def unaccent(text):
    return "".join(c for c in unicodedata.normalize("NFD", text or "")
                   if unicodedata.category(c) != "Mn")


def tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", unaccent(text).lower())
            if t not in STOP and len(t) > 1}


def nominal_score(source, candidate):
    """(cobertura dos tokens da fonte, interseção)."""
    a, b = tokens(source), tokens(candidate)
    overlap = a & b
    return (len(overlap) / len(a) if a else 0.0), len(overlap)


def distance_km(lat1, lon1, lat2, lon2):
    dy = (lat1 - lat2) * 111.32
    dx = (lon1 - lon2) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def load_municipios():
    raw = json.loads(MUNS.read_text(encoding="utf-8"))
    return {tuple(k.split("|")): (float(v[0]), float(v[1])) for k, v in raw.items()}


def places_search(key, query, bias=None):
    body = {"textQuery": query, "languageCode": "pt-BR", "maxResultCount": 5}
    if bias:
        body["locationBias"] = {"circle": {"center": {"latitude": bias[0], "longitude": bias[1]},
                                            "radius": bias[2]}}
    req = urllib.request.Request(
        "https://places.googleapis.com/v1/places:searchText",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.types",
            "User-Agent": "ile-axe-map-audit/1.0 (LABHDUFBA)",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response).get("places", [])


def target_context(feature, municipios):
    """Retorna query, centro esperado, raio, ou None se não houver contexto seguro."""
    p = feature["properties"]
    name = (p.get("nome") or "").strip()
    if not name or any(g in name.lower() for g in GENERICOS):
        return None
    municipality = unaccent((p.get("municipio") or "").strip().lower())
    uf = (p.get("uf") or "").strip().upper()
    key = (municipality, uf)
    if key in municipios:
        lat, lon = municipios[key]
        return f"{name}, {p.get('municipio')}, {uf}, Brasil", (lat, lon, 60.0)
    # A lista SEMUR/SEFAZ é estritamente municipal e só contém nome, sem endereço.
    if "sefaz" in (p.get("fontes") or []) and uf == "BA":
        return f"{name}, Salvador, BA, Brasil", (-12.9718, -38.5011, 35.0)
    return None


def select_place(name, places, expected):
    """Escolhe o único melhor candidato que passa nos gates semânticos e espaciais."""
    exp_lat, exp_lon, max_km = expected
    accepted = []
    for place in places:
        if "place_of_worship" not in place.get("types", []):
            continue
        loc = place.get("location") or {}
        if "latitude" not in loc or "longitude" not in loc:
            continue
        score, shared = nominal_score(name, place.get("displayName", {}).get("text", ""))
        dist = distance_km(float(loc["latitude"]), float(loc["longitude"]), exp_lat, exp_lon)
        if shared >= 2 and score >= 0.50 and dist <= max_km:
            accepted.append((score, -dist, place, round(dist, 2), shared))
    if not accepted:
        return None
    accepted.sort(reverse=True, key=lambda x: (x[0], x[1]))
    return accepted[0]


def main():
    key = os.environ.get("GMAPS_API_KEY")
    if not key:
        sys.exit("ABORT: defina GMAPS_API_KEY no ambiente. Nunca grave a chave no repo.")
    source = json.loads(SRC.read_text(encoding="utf-8"))
    features = source["features"]
    municipios = load_municipios()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    # Onda 1: Mapeando Axé cujo ponto atual diverge mais de 60 km do município declarado.
    target1 = []
    for i, feature in enumerate(features):
        p = feature["properties"]
        if "Mapeando" not in (p.get("fonte_label") or ""):
            continue
        ctx = target_context(feature, municipios)
        if not ctx:
            continue
        _, (lat0, lon0, _) = ctx
        lon, lat = feature["geometry"]["coordinates"]
        if distance_km(lat, lon, lat0, lon0) > 60:
            target1.append(i)

    # Onda 2: todos os pontos que a v4.2 identificou como em água.
    target2 = [i for i, f in enumerate(features)
               if f["properties"].get("geo_status") == "coordenada_agua"]
    targets = list(dict.fromkeys(target1 + target2))
    print(f"alvos: Mapeando Axé divergente={len(target1)}; coordenada_agua={len(target2)}; únicos={len(targets)}")

    accepted, unresolved, skipped, methods = [], [], [], Counter()
    for position, i in enumerate(targets, 1):
        feature = features[i]
        p = feature["properties"]
        ctx = target_context(feature, municipios)
        if not ctx:
            skipped.append(i)
            print(f"[{position}/{len(targets)}] sem contexto seguro: {p.get('nome','')[:44]}")
            continue
        query, expected = ctx
        if query in cache:
            places = cache[query]
            methods["cache"] += 1
        else:
            try:
                places = places_search(key, query, bias=(expected[0], expected[1], min(expected[2] * 1000, 50000)))
                cache[query] = places
                methods["places_api_new"] += 1
            except Exception as err:
                places = []
                cache[query] = []
                methods["erro_places"] += 1
            time.sleep(PAUSE_S)
        best = select_place(p.get("nome", ""), places, expected)
        if best:
            score, _, place, dist, shared = best
            accepted.append((i, place, score, dist, shared))
            print(f"[{position}/{len(targets)}] OK {p.get('nome','')[:38]:<38} score={score:.2f} dist={dist:.1f}km")
        else:
            unresolved.append(i)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    # Gera nova candidata a partir da v4.2, preservando toda a proveniência.
    out_features = []
    for feature in features:
        out_features.append({
            "type": feature.get("type", "Feature"),
            "geometry": dict(feature["geometry"]),
            "properties": dict(feature["properties"]),
        })
    for i, place, score, dist, shared in accepted:
        f = out_features[i]
        p = f["properties"]
        p["geo_status_anterior"] = p.get("geo_status", "")
        p["coord_origin_anterior"] = p.get("coord_origin", "")
        p["geo_status"] = "places_v44_validado"
        p["coord_origin"] = "places_api_new_v44"
        f["geometry"]["coordinates"] = [place["location"]["longitude"], place["location"]["latitude"]]
    for i in unresolved + skipped:
        p = out_features[i]["properties"]
        p["geo_status_anterior"] = p.get("geo_status", "")
        p["geo_status"] = "geocode_nao_resolvido"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "terreiros_nacional_v4_4.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": out_features}, ensure_ascii=False), encoding="utf-8")
    audit = {
        "base": "v4.2",
        "candidata": "v4.4",
        "total": len(out_features),
        "alvos_mapeando_axe_divergentes": len(target1),
        "alvos_coordenada_agua": len(target2),
        "alvos_unicos": len(targets),
        "places_validados": len(accepted),
        "nao_resolvidos": len(unresolved),
        "sem_contexto_seguro": len(skipped),
        "criterio": {
            "tipo_obrigatorio": "place_of_worship",
            "tokens_compartilhados_min": 2,
            "cobertura_nominal_min": 0.5,
            "distancia_max_km_municipio": 60,
            "distancia_max_km_sefaz_salvador": 35,
        },
        "por_metodo": dict(methods),
        "nota": "Place IDs, endereços e resposta bruta permanecem apenas no cache privado gitignored. "
                "A candidata pública preserva registros não resolvidos e os oculta por padrão, sem apagar dados.",
    }
    (OUT_DIR / "auditoria_v4_4.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print("resumo:", json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
