#!/usr/bin/env python3
"""Consolida os registros nacionais validados em GeoJSON v2."""

import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data"
MAPEANDO_VAL = BASE / "mapeando_axe" / "geocoding" / "google_places_v2_results.json"
UNIFIED_VAL = BASE / "unified" / "google_places_results.json"
OUTPUT = BASE / "unified" / "validation_all_sources_v2.geojson"

COLORS = {
    "confirmado": "#2d8f49",
    "confirmado_proximo": "#7ec850",
    "google_melhor": "#e8a838",
    "novo_google": "#c4700f",
    "novo_google_possivel": "#d4841a",
    "nominatim_melhor": "#557EB5",
    "divergente_inconclusivo": "#8b2c1c",
    "proximo_nome_diferente": "#a0522d",
    "nao_encontrado": "#555555",
    "match_ruim": "#cc3333",
    "sem_dados": "#999999",
}

GOOGLE_PREFERRED = {"google_melhor", "novo_google"}


def _valid_pair(lat, lng):
    return lat is not None and lng is not None


def select_coordinates(
    classification,
    original_lat,
    original_lng,
    google_lat,
    google_lng,
):
    """Seleciona coordenadas e registra sua proveniência."""
    if classification in GOOGLE_PREFERRED and _valid_pair(google_lat, google_lng):
        return float(google_lat), float(google_lng), "google"
    if _valid_pair(original_lat, original_lng):
        return float(original_lat), float(original_lng), "original"
    if classification == "novo_google_possivel" and _valid_pair(google_lat, google_lng):
        return float(google_lat), float(google_lng), "google_possivel"
    return None


def _feature(coords, properties):
    lat, lng, coordinate_source = coords
    properties["coordinate_source"] = coordinate_source
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": properties,
    }


def build_geojson(mapeando, unified):
    features = []

    for item in mapeando:
        classification = item.get("classification", "")
        google = item.get("google_best") or {}
        coords = select_coordinates(
            classification,
            item.get("nominatim_lat"),
            item.get("nominatim_lng"),
            google.get("lat"),
            google.get("lng"),
        )
        if coords is None:
            continue
        features.append(_feature(coords, {
            "id": f"mapeando_{item.get('source_record_id', '')}",
            "nome": item.get("name", ""),
            "cidade": item.get("city", ""),
            "uf": item.get("state", ""),
            "source": "mapeando_axe",
            "classification": classification,
            "google_name": google.get("name", ""),
            "google_address": google.get("address", ""),
            "google_lat": google.get("lat"),
            "google_lng": google.get("lng"),
            "original_lat": item.get("nominatim_lat"),
            "original_lng": item.get("nominatim_lng"),
            "google_sim": google.get("name_similarity"),
            "google_dist_m": google.get("distance_to_nominatim_m"),
            "color": COLORS.get(classification, "#999999"),
        }))

    for item in unified:
        classification = item.get("classification", "")
        coords = select_coordinates(
            classification,
            item.get("lat"),
            item.get("lng"),
            item.get("google_lat"),
            item.get("google_lng"),
        )
        if coords is None:
            continue
        features.append(_feature(coords, {
            "id": item.get("id", ""),
            "nome": item.get("nome", ""),
            "cidade": item.get("cidade", ""),
            "uf": item.get("uf", ""),
            "source": item.get("source", ""),
            "classification": classification,
            "google_name": item.get("google_name", ""),
            "google_address": item.get("google_address", ""),
            "google_lat": item.get("google_lat"),
            "google_lng": item.get("google_lng"),
            "original_lat": item.get("lat"),
            "original_lng": item.get("lng"),
            "color": COLORS.get(classification, "#999999"),
        }))

    return {"type": "FeatureCollection", "features": features}


def main():
    mapeando = json.loads(MAPEANDO_VAL.read_text(encoding="utf-8"))
    unified = json.loads(UNIFIED_VAL.read_text(encoding="utf-8"))
    geojson = build_geojson(mapeando, unified)
    OUTPUT.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")

    features = geojson["features"]
    sources = Counter(f["properties"]["source"] for f in features)
    classes = Counter(f["properties"]["classification"] for f in features)
    coordinate_sources = Counter(f["properties"]["coordinate_source"] for f in features)
    print(f"Total features: {len(features)}")
    print("Por fonte:", dict(sources))
    print("Por classificação:", dict(classes))
    print("Por coordenada:", dict(coordinate_sources))
    print(f"GeoJSON: {OUTPUT} ({OUTPUT.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
