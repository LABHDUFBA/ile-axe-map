#!/usr/bin/env python3
"""
Gera GeoJSON de teste com os resultados da validação cruzada Google Places vs Nominatim.
Estratégia: para cada registro, escolhe a melhor coordenada disponível.
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RESULTS_PATH = BASE / "data" / "mapeando_axe" / "geocoding" / "google_places_v2_results.json"
OUTPUT_PATH = BASE / "data" / "mapeando_axe" / "geocoding" / "validation_test_map.geojson"

# Cores por classificação (para o mapa)
CLASS_COLORS = {
    "confirmado": "#2ecc71",           # verde — ambos concordam
    "confirmado_proximo": "#27ae60",    # verde escuro — ambos concordam (~500m)
    "google_melhor": "#3498db",         # azul — Google mais confiável (endereço atualizado)
    "novo_google": "#e67e22",           # laranja — só Google achou
    "novo_google_possivel": "#f39c12",  # amarelo/laranja claro — Google possivel
    "nominatim_melhor": "#9b59b6",      # roxo — manter Nominatim
    "divergente_inconclusivo": "#e74c3c", # vermelho — inconclusivo
    "proximo_nome_diferente": "#c0392b", # vermelho escuro
    "match_ruim": "#95a5a6",            # cinza — descartar
    "nao_encontrado": "#bdc3c7",        # cinza claro
    "sem_dados": "#bdc3c7",
}

with open(RESULTS_PATH) as f:
    results = json.load(f)

features = []

for r in results:
    cls = r["classification"]
    g = r.get("google_best")
    nom_lat = r.get("nominatim_lat")
    nom_lng = r.get("nominatim_lng")

    # Escolher coordenada: priorizar Google se for confiável, senão Nominatim
    use_google = cls in ("confirmado", "confirmado_proximo", "google_melhor", "novo_google", "novo_google_possivel")
    use_nominatim = cls in ("nominatim_melhor", "divergente_inconclusivo", "proximo_nome_diferente")
    
    # Para confirmado, usar Google (endereço mais atual)
    if use_google and g and g.get("lat"):
        lat, lng = g["lat"], g["lng"]
        source = "google"
    elif use_nominatim and nom_lat is not None:
        lat, lng = nom_lat, nom_lng
        source = "nominatim"
    elif g and g.get("lat") and cls not in ("nominatim_melhor", "nao_encontrado", "sem_dados"):
        # Fallback: se tem Google e não é explicitamente Nominatim-melhor, usar Google
        lat, lng = g["lat"], g["lng"]
        source = "google"
    elif nom_lat is not None:
        lat, lng = nom_lat, nom_lng
        source = "nominatim"
    else:
        continue  # sem coordenadas

    # Nome para exibição
    display_name = r.get("name", "")
    google_name = g.get("name", "") if g else ""
    
    props = {
        "name": display_name,
        "city": r.get("city", ""),
        "state": r.get("state", ""),
        "classification": cls,
        "source": source,
        "color": CLASS_COLORS.get(cls, "#777777"),
        "google_name": google_name,
        "google_name_similarity": g.get("name_similarity") if g else None,
        "google_city_match": g.get("city_match") if g else None,
        "google_address": g.get("address", "") if g else "",
        "google_rating": g.get("rating") if g else None,
        "google_reviews": g.get("user_ratings_total") if g else None,
        "nominatim_precision": r.get("nominatim_precision"),
        "distance_m": g.get("distance_to_nominatim_m") if g else None,
    }

    features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": props,
    })

geojson = {"type": "FeatureCollection", "features": features}

with open(OUTPUT_PATH, "w") as f:
    json.dump(geojson, f, indent=2, ensure_ascii=False)

print(f"GeoJSON gerado: {OUTPUT_PATH}")
print(f"Features: {len(features)}")

# Estatísticas
from collections import Counter
sources = Counter(f["properties"]["source"] for f in features)
classes = Counter(f["properties"]["classification"] for f in features)
print(f"\nPor fonte: {dict(sources)}")
print(f"Por classe: {dict(classes)}")