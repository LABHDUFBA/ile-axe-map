#!/usr/bin/env python3
"""Candidata v4.5: re-geocodificação completa com Places API (New) e gate estrito.

Parte da v4.2 (fonte auditada). Classes-alvo:
  A. centroide_suspeito com município validável (~398)
  B. uf_divergente com município validável (~14)
  C. re-análise dos não-resolvidos das ondas 1-2 da v4.4 (261) com gate atualizado

Gate (tudo obrigatório):
  - tipo Places: place_of_worship presente E tipo 'church' AUSENTE
    (rejeita paróquias católicas que casam com nomes de santos);
  - >=2 tokens distintivos compartilhados com o nome do registro;
  - cobertura nominal >=0.50 sobre tokens ampliados;
  - distância <=60 km do centróide do município declarado.

Uso: GMAPS_API_KEY=... python3 scripts/regeocode_places_v45.py
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
OUT_DIR = ROOT / "data/v4_5"
CACHE = ROOT / "data/places_cache_v45.json"  # gitignored: contém Place IDs e endereços
PAUSE_S = 0.11

BASE = {"a", "as", "o", "os", "de", "da", "das", "do", "dos", "e", "em", "para", "com",
        "ile", "yle", "ile", "axe", "ase", "asa", "terreiro", "casa", "centro", "espirita",
        "umbanda", "candomble", "religioso", "religiosa", "afro", "africano", "africana"}
EXTRA = {"templo", "tenda", "reino", "associacao", "sociedade", "beneficente",
         "mae", "pai", "santo", "santa", "sao", "caboclo", "cabocla"}
STOP = BASE | EXTRA
GENERICOS = ("sem nome", "terreiro sem", "casa sem")


def unaccent(text):
    return "".join(c for c in unicodedata.normalize("NFD", text or "")
                   if unicodedata.category(c) != "Mn")


def tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", unaccent(text).lower())
            if t not in STOP and len(t) > 1}


def nominal_score(source, candidate):
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


def places_search(key, query, bias):
    body = {"textQuery": query, "languageCode": "pt-BR", "maxResultCount": 5,
            "locationBias": {"circle": {"center": {"latitude": bias[0], "longitude": bias[1]},
                                        "radius": 50000.0}}}
    req = urllib.request.Request(
        "https://places.googleapis.com/v1/places:searchText",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "X-Goog-Api-Key": key,
                 "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.types",
                 "User-Agent": "ile-axe-map-audit/1.0 (LABHDUFBA)"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response).get("places", [])


def gate(nome, place, expected):
    """Retorna (score, dist) se aprovado, None caso contrário."""
    types = set(place.get("types", []))
    if "place_of_worship" not in types or "church" in types:
        return None
    loc = place.get("location") or {}
    if "latitude" not in loc or "longitude" not in loc:
        return None
    cov, shared = nominal_score(nome, place.get("displayName", {}).get("text", ""))
    if shared < 2 or cov < 0.50:
        return None
    dist = distance_km(float(loc["latitude"]), float(loc["longitude"]), expected[0], expected[1])
    if dist > expected[2]:
        return None
    return cov, dist


def context(feature, municipios):
    """(nome, query, (lat, lon, raio_km)) ou None."""
    p = feature["properties"]
    nome = (p.get("nome") or "").strip()
    if not nome or any(g in nome.lower() for g in GENERICOS):
        return None
    municipality = unaccent((p.get("municipio") or "").strip().lower())
    uf = (p.get("uf") or "").strip().upper()
    key = (municipality, uf)
    if key in municipios:
        lat, lon = municipios[key]
        return nome, f"{nome}, {p.get('municipio')}, {uf}, Brasil", (lat, lon, 60.0)
    if "sefaz" in (p.get("fontes") or []) and uf == "BA":
        return nome, f"{nome}, Salvador, BA, Brasil", (-12.9718, -38.5011, 35.0)
    return None


def main():
    key = os.environ.get("GMAPS_API_KEY")
    if not key:
        sys.exit("ABORT: defina GMAPS_API_KEY no ambiente. Nunca grave a chave no repo.")
    source = json.loads(SRC.read_text(encoding="utf-8"))
    features = source["features"]
    municipios = load_municipios()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    v44path = ROOT / "data/v4_4/terreiros_nacional_v4_4.geojson"
    v44 = json.loads(v44path.read_text(encoding="utf-8"))["features"] if v44path.exists() else []
    resolved_prev = {i for i, f in enumerate(v44)
                     if f["properties"].get("geo_status") == "places_v44_validado"} if v44 else set()

    # Alvos A/B: centroide_suspeito e uf_divergente com contexto municipal seguro.
    targets_ab = []
    for i, f in enumerate(features):
        p = f["properties"]
        gs = str(p.get("geo_status", ""))
        if gs not in ("centroide_suspeito", "uf_divergente"):
            continue
        if context(f, municipios):
            targets_ab.append(i)

    # Alvo C: não-resolvidos da v4.4 (re-análise com gate ampliado),
    # excluindo os que a v4.4 já resolveu (mantêm seu status validado).
    targets_c = [i for i in range(len(features))
                 if i not in resolved_prev
                 and i < len(v44)
                 and v44[i]["properties"].get("geo_status") == "geocode_nao_resolvido"
                 and context(features[i], municipios)]

    targets = list(dict.fromkeys(targets_ab + targets_c))
    print(f"alvos A/B (centroide+uf_div com municipio): {len(targets_ab)}")
    print(f"alvo C (nao-resolvidos v4.4 re-analisaveis): {len(targets_c)}")
    print(f"total unico: {len(targets)}")

    accepted, unresolved, methods = [], [], Counter()
    for position, i in enumerate(targets, 1):
        f = features[i]
        nome, query, expected = context(f, municipios)
        if query in cache:
            places = cache[query]
            methods["cache"] += 1
        else:
            try:
                places = places_search(key, query, (expected[0], expected[1]))
                methods["places_api_new"] += 1
            except Exception:
                places = []
                methods["erro"] += 1
            cache[query] = places
            time.sleep(PAUSE_S)
        best = None
        for place in places:
            verdict = gate(nome, place, expected)
            if verdict and (best is None or verdict > best[:2]):
                best = (verdict[0], verdict[1], place)
        if best:
            accepted.append((i, best[2], best[0], best[1]))
            if position % 20 == 0 or position == len(targets):
                print(f"  [{position}/{len(targets)}] acumulado aceito={len(accepted)}")
        else:
            unresolved.append(i)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    # Candidata v4.5 a partir da v4.2, preservando tudo.
    out = []
    for f in features:
        out.append({"type": f.get("type", "Feature"),
                    "geometry": dict(f["geometry"]),
                    "properties": dict(f["properties"])})
    for i, place, cov, dist in accepted:
        p = out[i]["properties"]
        p["geo_status_anterior"] = p.get("geo_status", "")
        p["coord_origin_anterior"] = p.get("coord_origin", "")
        p["geo_status"] = "places_v45_validado"
        p["coord_origin"] = "places_api_new_v45"
        out[i]["geometry"]["coordinates"] = [place["location"]["longitude"], place["location"]["latitude"]]
    resolved_set = {i for i, _, _, _ in accepted}
    for i in unresolved:
        if i in resolved_set:
            continue
        p = out[i]["properties"]
        p["geo_status_anterior"] = p.get("geo_status", "")
        p["geo_status"] = "geocode_nao_resolvido"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "terreiros_nacional_v4_5.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": out}, ensure_ascii=False), encoding="utf-8")

    prev_status = Counter()
    for i, _, _, _ in accepted:
        prev_status[features[i]["properties"].get("geo_status", "")] += 1
    audit = {
        "base": "v4.2", "candidata": "v4.5", "total": len(out),
        "alvos_ab": len(targets_ab), "alvo_c_reanalisaveis": len(targets_c),
        "total_unicos": len(targets),
        "places_validados": len(accepted),
        "por_status_anterior": dict(prev_status),
        "nao_resolvidos": len(unresolved),
        "criterio": {
            "tipo_obrigatorio": "place_of_worship", "tipo_vedado": "church",
            "tokens_compartilhados_min": 2, "cobertura_nominal_min": 0.5,
            "distancia_max_km_municipio": 60, "distancia_max_km_sefaz_salvador": 35,
        },
        "por_metodo": dict(methods),
        "nota": "Places API (New) com rejeicao de tipo church (paroquias catolicas), "
                "gate nominal ampliado e validacao municipal. Nao-resolvidos preservados "
                "e ocultos por padrao. Cache privado gitignored.",
    }
    (OUT_DIR / "auditoria_v4_5.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print("resumo:", json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
